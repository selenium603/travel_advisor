"""
Crew Orchestrator — the main pipeline that:
1. Uses AI to parse the user request (Travel Manager)
2. Fetches real data from APIs in parallel (no AI)
3. Uses AI to compile the final itinerary (Itinerary Compiler)

This reduces LLM calls from ~15-20 down to 2-3.
"""

import asyncio
import json
import logging
from typing import Optional, Callable, Awaitable

from backend.config.settings import settings  # Set project-local CrewAI storage before import.
from crewai import Crew, Process

from backend.agents.definitions import (
    create_travel_manager,
    create_parameter_repair_agent,
    create_travel_knowledge_agent,
    create_itinerary_compiler,
)
from backend.agents.tasks import (
    create_planning_task,
    create_repair_task,
    create_knowledge_task,
    create_compilation_task,
)
from backend.agents.tools import TravelKnowledgeTool
from backend.services.flights import FlightService
from backend.services.accommodation import AccommodationService
from backend.services.activities import ActivityService
from backend.services.logistics import LogisticsService
from backend.services.knowledge.rag import RAGService
from backend.crew.plan_params import PlanParamsError, validate_plan_params
from backend.models.schemas import (
    FlightSearchResult,
    AccommodationSearchResult,
    ActivitySearchResult,
    LogisticsResult,
    TravelFormDetails,
    TravelPlanParams,
)

logger = logging.getLogger(__name__)

# Type for progress callback
ProgressCallback = Optional[Callable[[str, str, str], Awaitable[None]]]
TextCallback = Optional[Callable[[str], Awaitable[None]]]
ParamsCallback = Optional[Callable[[TravelPlanParams], Awaitable[None]]]


def _planning_values(output) -> dict:
    """Read CrewAI's typed result, accepting plain JSON only as a repairable fallback."""
    if output.pydantic is not None:
        return output.pydantic.model_dump()
    if output.json_dict is not None:
        return output.json_dict
    try:
        values = json.loads(output.raw)
    except (TypeError, json.JSONDecodeError) as exc:
        raise PlanParamsError("规划 Agent 未返回有效的结构化参数") from exc
    if not isinstance(values, dict):
        raise PlanParamsError("规划 Agent 返回的参数必须是对象")
    return values


def _format_flights(data: FlightSearchResult) -> str:
    """Format flight data into readable text for the AI compiler."""
    if data.raw_response:
        return f"**Source:** {data.source}\n\n{data.raw_response}"
    if not data.options:
        return "No flight data available."

    lines = [f"**Route:** {data.origin} -> {data.destination}"]
    lines.append(f"**Date:** {data.departure_date}")
    if data.return_date:
        lines.append(f"**Return:** {data.return_date}")
    lines.append(f"**Travelers:** {data.travelers} | **Class:** {data.cabin_class}")
    lines.append(f"**Source:** {data.source}\n")

    for i, opt in enumerate(data.options[:5], 1):
        segments_str = " -> ".join(
            f"{s.departure_airport} to {s.arrival_airport} ({s.airline} {s.flight_number})"
            for s in opt.segments
        )
        lines.append(f"### Option {i}: ${opt.price_per_person}/person")
        lines.append(f"- Segments: {segments_str}")
        lines.append(f"- Total Duration: {opt.total_duration}")
        lines.append(f"- Layovers: {opt.layovers}")
        if opt.layover_cities:
            lines.append(f"- Layover Cities: {', '.join(opt.layover_cities)}")
        lines.append(f"- Total Price: ${opt.total_price} {opt.currency}")
        lines.append(f"- Baggage: {opt.baggage}")
        if opt.booking_url:
            lines.append(f"- Book: {opt.booking_url}")
        lines.append("")

    return "\n".join(lines)


def _format_accommodation(data: AccommodationSearchResult) -> str:
    """Format accommodation data into readable text."""
    if data.raw_response:
        return f"**Source:** {data.source}\n\n{data.raw_response}"
    if not data.options:
        return "No accommodation data available."

    lines = [f"**Location:** {data.destination}"]
    lines.append(f"**Dates:** {data.check_in} to {data.check_out} ({data.nights} nights)")
    lines.append(f"**Guests:** {data.guests} | **Source:** {data.source}\n")

    for i, opt in enumerate(data.options[:8], 1):
        lines.append(f"### Option {i}: {opt.name} ({opt.provider})")
        lines.append(f"- Type: {opt.property_type}")
        lines.append(f"- Rating: {opt.rating}/5 ({opt.review_count} reviews)")
        lines.append(f"- Price: ${opt.price_per_night}/night | Total: ${opt.total_price}")
        if opt.neighborhood:
            lines.append(f"- Neighborhood: {opt.neighborhood}")
        if opt.amenities:
            lines.append(f"- Amenities: {', '.join(opt.amenities[:8])}")
        lines.append(f"- Cancellation: {opt.cancellation_policy}")
        lines.append(f"- Breakfast: {'Included' if opt.breakfast_included else 'Not included'}")
        if opt.booking_url:
            lines.append(f"- Book: {opt.booking_url}")
        lines.append("")

    return "\n".join(lines)


def _format_activities(data: ActivitySearchResult) -> str:
    """Format activity data into readable text."""
    lines = [f"**Destination:** {data.destination}"]
    lines.append(f"**Interests:** {', '.join(data.interests)}\n")

    if data.attractions:
        lines.append("## Attractions & Places")
        for i, a in enumerate(data.attractions[:8], 1):
            lines.append(f"{i}. **{a.name}** — {a.category}")
            if a.rating:
                lines.append(f"   Rating: {a.rating}/5 ({a.review_count} reviews)")
            if a.address:
                lines.append(f"   Address: {a.address}")
            if a.price:
                lines.append(f"   Approx. cost: {a.price} {a.currency}")
            if a.opening_hours:
                lines.append(f"   Hours: {a.opening_hours}")
        lines.append("")

    if data.tours:
        lines.append("## Tours & Experiences (Bookable)")
        for i, t in enumerate(data.tours[:8], 1):
            lines.append(f"{i}. **{t.name}**")
            lines.append(f"   {t.description}")
            lines.append(f"   Rating: {t.rating}/5 ({t.review_count} reviews)")
            if t.price:
                lines.append(f"   Price: ${t.price}/person")
            if t.duration:
                lines.append(f"   Duration: {t.duration}")
            if t.booking_url:
                lines.append(f"   Book: {t.booking_url}")
        lines.append("")

    if data.dining:
        lines.append("## Restaurants & Dining")
        for i, d in enumerate(data.dining[:8], 1):
            lines.append(f"{i}. **{d.name}** — {d.category}")
            if d.rating:
                lines.append(f"   Rating: {d.rating}/5 ({d.review_count} reviews)")
            if d.address:
                lines.append(f"   Address: {d.address}")
            if d.price:
                lines.append(f"   Approx. cost: {d.price} {d.currency}/person")
            if d.booking_url:
                lines.append(f"   Link: {d.booking_url}")
        lines.append("")

    if not data.attractions and not data.tours and not data.dining:
        lines.append("No activity data available.")

    return "\n".join(lines)


def _format_logistics(data: LogisticsResult) -> str:
    """Format logistics data into readable text."""
    lines = []

    if data.routes:
        lines.append("## Transport Routes")
        for r in data.routes:
            source = f" ({r.provider})" if r.provider else ""
            lines.append(f"- **{r.mode.title()}{source}:** {r.origin} -> {r.destination}")
            lines.append(f"  Distance: {r.distance} | Duration: {r.duration}")
            if r.fare:
                lines.append(f"  Fare: {r.fare}")
            for step in r.steps[:3]:
                lines.append(f"  - {step}")
        lines.append("")

    if data.weather:
        lines.append("## Weather Forecast")
        for w in data.weather:
            summary = (
                f"- {w.date}: {w.description}, "
                f"High {w.temperature_high}C / Low {w.temperature_low}C"
            )
            if w.humidity is not None:
                summary += f", Humidity {w.humidity}%"
            if w.wind_speed is not None:
                summary += f", Wind {w.wind_speed} m/s"
            lines.append(summary)
        lines.append("")

    if data.currency:
        lines.append("## Currency")
        lines.append(
            f"1 {data.currency.base_currency} = "
            f"{data.currency.rate} {data.currency.target_currency}"
        )
        lines.append("")

    if data.country:
        c = data.country
        lines.append("## Country Information")
        lines.append(f"- **Country:** {c.name}")
        lines.append(f"- **Capital:** {c.capital}")
        lines.append(f"- **Currency:** {c.currency_name} ({c.currency_code})")
        lines.append(f"- **Languages:** {', '.join(c.languages)}")
        lines.append(f"- **Timezone:** {c.timezone}")
        lines.append(f"- **Calling Code:** {c.calling_code}")
        if c.visa_info:
            lines.append(f"- **Visa:** {c.visa_info}")
        if c.vaccinations:
            lines.append(f"- **Vaccinations:** {c.vaccinations}")
        if c.safety_info:
            lines.append(f"- **Safety:** {c.safety_info}")
        if c.electricity:
            lines.append(f"- **Electricity:** {c.electricity}")
        lines.append("")

    if not lines:
        return "No logistics data available."

    return "\n".join(lines)


async def _resolve_plan_params(
    user_request: str, form_details: TravelFormDetails | None,
    memory_context: str = "",
):
    """Get typed parameters, allowing exactly one repair after validation fails."""
    manager = create_travel_manager()
    planning_crew = Crew(
        agents=[manager], tasks=[create_planning_task(manager, user_request, memory_context)],
        process=Process.sequential, verbose=True,
    )
    planning_output = await asyncio.to_thread(planning_crew.kickoff)
    try:
        return validate_plan_params(_planning_values(planning_output), form_details)
    except PlanParamsError as first_error:
        logger.warning("Planning parameters invalid; requesting one repair: %s", first_error)
        repair_agent = create_parameter_repair_agent()
        repair_crew = Crew(
            agents=[repair_agent],
            tasks=[create_repair_task(
                repair_agent, user_request, str(planning_output), str(first_error)
            )],
            process=Process.sequential, verbose=True,
        )
        repaired_output = await asyncio.to_thread(repair_crew.kickoff)
        try:
            return validate_plan_params(_planning_values(repaired_output), form_details)
        except PlanParamsError as second_error:
            raise PlanParamsError(f"旅行参数修复后仍无效：{second_error}") from second_error


async def run_travel_pipeline(
    user_request: str,
    progress_callback: ProgressCallback = None,
    text_callback: TextCallback = None,
    form_details: TravelFormDetails | None = None,
    memory_context: str = "",
    params_callback: ParamsCallback = None,
) -> str:
    """
    Main pipeline:
    1. AI parses user request -> structured params
    2. APIs fetch real data in parallel (no AI)
    3. AI compiles final itinerary from real data

    Args:
        user_request: Natural language travel request
        progress_callback: Optional async callback(step_key, label, status)
        text_callback: Optional async callback for final itinerary text chunks

    Returns:
        Final itinerary as string
    """

    async def notify(key: str, label: str, status: str):
        if progress_callback:
            await progress_callback(key, label, status)

    # ── Step 1: AI parses user request ────────────────────────────────────
    await notify("planning", "Travel Planning Manager", "running")
    logger.info("Step 1: Parsing user request with AI...")

    loop = asyncio.get_running_loop()
    params = await _resolve_plan_params(user_request, form_details, memory_context)
    if params_callback:
        await params_callback(params)
    planning_result = params.model_dump_json(indent=2)
    await notify("planning", "Travel Planning Manager", "completed")
    logger.info("Validated planning parameters: %s", planning_result[:500])
    try:
        provider_preferences = json.loads(memory_context).get("long_term_preferences", {})
    except (TypeError, json.JSONDecodeError, AttributeError):
        provider_preferences = {}
    provider_context = (
        f"{user_request}\nCurrent trip and form values override long-term preferences: "
        f"{json.dumps(provider_preferences, ensure_ascii=False)}"
    )

    # ── Step 2: Fetch real data from APIs in parallel (NO AI) ─────────────
    await notify("data_fetch", "Fetching Real-Time Data", "running")
    logger.info("Step 2: Fetching real-time data from APIs...")

    flight_service = FlightService()
    accommodation_service = AccommodationService()
    activity_service = ActivityService()
    logistics_service = LogisticsService()

    # All API calls happen in parallel — pure HTTP, no LLM
    flights_task = flight_service.search(
        origin=params.origin,
        destination=params.destinations[0],
        departure_date=params.departure_date.isoformat(),
        return_date=params.return_date.isoformat(),
        travelers=params.travelers,
        cabin_class=params.cabin_class,
        request_context=provider_context,
    )

    accommodation_task = accommodation_service.search(
        destination=params.destinations[0],
        check_in=params.departure_date.isoformat(),
        check_out=params.return_date.isoformat(),
        guests=params.travelers,
        request_context=provider_context,
    )

    activities_task = activity_service.search(
        destination=params.destinations[0],
        interests=params.interests,
    )

    logistics_task = logistics_service.get_logistics(
        destination_city=params.destinations[0],
        destination_country=params.destination_country,
        origin=params.origin,
    )

    # Execute all in parallel
    flights_data, accommodation_data, activities_data, logistics_data = await asyncio.gather(
        flights_task,
        accommodation_task,
        activities_task,
        logistics_task,
    )

    if activities_data.attractions:
        names = [place.name for place in activities_data.attractions[:3]]
        logistics_data.routes.extend(
            await logistics_service.get_local_routes(params.destinations[0], names)
        )

    await notify("data_fetch", "Fetching Real-Time Data", "completed")
    logger.info("All API data fetched successfully")

    # ── Step 3: AI Knowledge Expert ─────────────────────────────────────
    await notify("knowledge", "Travel Knowledge Expert", "running")
    logger.info("Step 3: Getting travel knowledge from RAG...")

    rag = await loop.run_in_executor(None, RAGService)
    if rag._collection is None:
        logger.warning("Travel knowledge is unavailable; continuing without local knowledge")
        knowledge_result = "知识库暂不可用；不提供未经核实的文化、签证或当地信息。"
    else:
        knowledge_tool = TravelKnowledgeTool()
        knowledge_agent = create_travel_knowledge_agent(tools=[knowledge_tool])
        knowledge_task_obj = create_knowledge_task(
            knowledge_agent,
            destination=", ".join(params.destinations),
        )

        knowledge_crew = Crew(
            agents=[knowledge_agent],
            tasks=[knowledge_task_obj],
            process=Process.sequential,
            verbose=True,
        )

        knowledge_result = str(await loop.run_in_executor(None, knowledge_crew.kickoff))
    await notify("knowledge", "Travel Knowledge Expert", "completed")

    # ── Step 4: AI compiles final itinerary ──────────────────────────────
    await notify("compilation", "Itinerary Compiler & Optimizer", "running")
    logger.info("Step 4: Compiling itinerary with AI...")

    # Format all API data into readable text
    flights_text = _format_flights(flights_data)
    accommodation_text = _format_accommodation(accommodation_data)
    activities_text = _format_activities(activities_data)
    logistics_text = _format_logistics(logistics_data)

    compiler = create_itinerary_compiler()
    compilation_task_obj = create_compilation_task(
        agent=compiler,
        user_request=user_request,
        planning_output=planning_result,
        flights_data=flights_text,
        accommodation_data=accommodation_text,
        activities_data=activities_text,
        logistics_data=logistics_text,
        knowledge_output=knowledge_result,
        memory_context=memory_context,
    )

    compilation_crew = Crew(
        agents=[compiler],
        tasks=[compilation_task_obj],
        process=Process.sequential,
        verbose=True,
        stream=text_callback is not None,
    )

    if text_callback is None:
        final_result = str(await loop.run_in_executor(None, compilation_crew.kickoff))
    else:
        queue: asyncio.Queue[str | None] = asyncio.Queue()

        def run_stream() -> str:
            try:
                streaming = compilation_crew.kickoff()
                for chunk in streaming:
                    if chunk.content and chunk.chunk_type.value == "text":
                        loop.call_soon_threadsafe(queue.put_nowait, chunk.content)
                return str(streaming.result)
            finally:
                loop.call_soon_threadsafe(queue.put_nowait, None)

        worker = asyncio.create_task(asyncio.to_thread(run_stream))
        while (piece := await queue.get()) is not None:
            await text_callback(piece)
        final_result = await worker
    await notify("compilation", "Itinerary Compiler & Optimizer", "completed")

    logger.info(f"Itinerary compiled. Length: {len(final_result)} chars")
    return final_result


def run_pipeline_sync(user_request: str) -> str:
    """Synchronous wrapper for the async pipeline."""
    return asyncio.run(run_travel_pipeline(user_request))
