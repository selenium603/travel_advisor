"""
Task definitions for the 3 remaining AI agents.
"""

from crewai import Task, Agent


def create_planning_task(agent: Agent, user_request: str) -> Task:
    """
    Travel Manager's task: parse natural language into structured parameters.
    """
    return Task(
        description=(
            f"Analyze this travel request and extract structured parameters:\n\n"
            f"{user_request}\n\n"
            f"Extract and output as a clear structured format:\n"
            f"1. Destination(s) — city names and countries\n"
            f"2. Origin city (if mentioned, otherwise assume a major hub)\n"
            f"3. Duration — number of days\n"
            f"4. Travel dates or approximate timeframe\n"
            f"5. Number of travelers and any special needs\n"
            f"6. Budget level (luxury, mid-range, budget)\n"
            f"7. Key interests (food, history, art, adventure, culture, nightlife, etc.)\n"
            f"8. Preferred cabin class for flights\n"
            f"9. Any specific requirements (dietary, accessibility, etc.)\n\n"
            f"If information is missing, fill in sensible defaults.\n"
            f"Output ONLY the structured breakdown, no additional commentary."
        ),
        expected_output=(
            "A structured breakdown with these exact fields:\n"
            "- Destinations: [list of cities]\n"
            "- Origin: [city]\n"
            "- Duration: [N days]\n"
            "- Dates: [departure and return dates or 'flexible']\n"
            "- Travelers: [number and type]\n"
            "- Budget: [level]\n"
            "- Interests: [list]\n"
            "- Cabin Class: [economy/business/first]\n"
            "- Special Requirements: [list or 'none']\n"
            "- Suggested Split: [e.g., '3 days Rome, 2 days Florence']"
        ),
        agent=agent,
    )


def create_knowledge_task(agent: Agent, destination: str) -> Task:
    """
    Knowledge Expert's task: provide cultural and practical travel info.
    """
    return Task(
        description=(
            f"Provide comprehensive travel knowledge for: {destination}\n\n"
            f"Research and provide information on:\n"
            f"1. Visa requirements and entry procedures\n"
            f"2. Cultural etiquette and customs\n"
            f"3. Best time to visit and weather considerations\n"
            f"4. Currency, payment methods, and tipping practices\n"
            f"5. Safety tips and travel advisories\n"
            f"6. Packing recommendations\n"
            f"7. Local customs and dining etiquette\n"
            f"8. Any destination-specific tips\n\n"
            f"Use the travel knowledge base for every factual claim and cite its source filename. "
            f"If retrieval says no matching material or is unavailable, say which topics lack "
            f"verified material and do not invent an answer. Do not present dated visa, entry, "
            f"price, or opening-hour information as current."
        ),
        expected_output=(
            "A source-cited guide limited to retrieved facts, with explicit gaps where the "
            "knowledge base has no relevant material or current official verification."
        ),
        agent=agent,
    )


def create_compilation_task(
    agent: Agent,
    user_request: str,
    planning_output: str,
    flights_data: str,
    accommodation_data: str,
    activities_data: str,
    logistics_data: str,
    knowledge_output: str,
) -> Task:
    """
    Itinerary Compiler's task: synthesize all data into a day-by-day plan.
    Real API data is passed directly as context — no extra LLM calls needed to fetch it.
    """
    return Task(
        description=(
            f"Create a comprehensive, day-by-day travel itinerary using the real-time data below.\n\n"
            f"## Original Request\n{user_request}\n\n"
            f"## Travel Plan Parameters\n{planning_output}\n\n"
            f"## Available Flights (Provider response)\n{flights_data}\n\n"
            f"## Available Accommodation (Provider response)\n{accommodation_data}\n\n"
            f"## Activities, Attractions & Dining (Real-time data)\n{activities_data}\n\n"
            f"## Logistics: Transport, Weather, Currency, Country Info\n{logistics_data}\n\n"
            f"## Cultural & Practical Knowledge\n{knowledge_output}\n\n"
            f"INSTRUCTIONS:\n"
            f"1. Create a day-by-day itinerary using ONLY the provider data provided above; do not invent missing prices or links\n"
            f"2. Select the best flight option and recommend it with reasoning\n"
            f"3. Select the best accommodation and explain why\n"
            f"4. Schedule activities logically — group by neighborhood, consider timing\n"
            f"5. Include restaurant recommendations from the dining data for each day\n"
            f"6. Add transport details between locations\n"
            f"7. Include weather-appropriate suggestions\n"
            f"8. Add cultural tips and practical advice throughout\n"
            f"9. Build in realistic timing and flexibility\n"
            f"10. Provide a total budget summary at the end\n"
            f"11. Include booking URLs where available\n"
            f"12. Write every user-facing heading, label, explanation, and recommendation in Simplified Chinese. "
            f"Keep proper names, provider names, currency codes, and URLs unchanged where appropriate.\n"
            f"13. If flight data lacks a verified offer for the requested date, say that no bookable offer was verified. "
            f"Do not claim the route has no scheduled flights. Never present a generic search link as a specific flight.\n"
            f"14. If the knowledge section reports no match, do not invent cultural, visa, or local facts to fill it.\n"
        ),
        expected_output=(
            "A complete, beautifully formatted day-by-day itinerary including:\n"
            "- Trip Overview (destinations, dates, duration)\n"
            "- Recommended Flight with booking details\n"
            "- Recommended Accommodation with booking details\n"
            "- Daily Breakdown with:\n"
            "  * Morning/Afternoon/Evening activities with times\n"
            "  * Restaurant recommendations for each meal\n"
            "  * Transportation between activities\n"
            "  * Estimated costs per activity\n"
            "- Weather forecast for the trip dates\n"
            "- Practical Information (visa, currency, tips, packing)\n"
            "- Budget Summary (flights, hotels, activities, food, transport)\n"
            "- Pre-Trip Checklist (bookings to make, what to pack)\n"
            "- Booking Links for all recommended services\n\n"
            "Use Simplified Chinese throughout the final answer. Format should be clear, detailed, and ready to use."
        ),
        agent=agent,
    )
