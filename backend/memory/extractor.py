"""Extract only explicit durable preference updates from a user's own words."""

import asyncio

from crewai import Agent, Crew, Process, Task

from backend.agents.llm import create_gemini_llm
from backend.models.schemas import PreferenceExtraction, PreferenceUpdate


EXPLICIT_MARKERS = (
    "以后", "今后", "长期", "每次", "总是", "通常", "一贯",
    "我喜欢", "我更喜欢", "我不喜欢", "我偏好", "我更偏好",
    "from now on", "always prefer", "i prefer", "i like", "i dislike",
)
ONE_TRIP_MARKERS = ("这次", "本次", "这趟", "此次", "this trip")


def may_contain_durable_preference(message: str) -> bool:
    lowered = message.casefold()
    return any(marker in lowered for marker in EXPLICIT_MARKERS)


def _extract_sync(message: str) -> list[PreferenceUpdate]:
    agent = Agent(
        role="Travel Preference Memory Curator",
        goal="Extract explicit, durable personal travel preferences without inference.",
        backstory="You update a user's profile only when their own words clearly state a recurring preference.",
        llm=create_gemini_llm(),
        allow_delegation=False,
        max_iter=2,
        verbose=False,
    )
    task = Task(
        description=(
            "Read only the user's message below. Extract durable preferences for these "
            "categories: lodging, food, pace, sights, budget. A one-trip destination, date, "
            "traveler count, or form selection is NOT a durable preference. Statements about "
            "future or habitual choices are. For each update return category, a short clear "
            "value in the user's language, and source_quote copied exactly from the message. "
            "An explicit change replaces the older preference in the same category. "
            "Do not infer unstated preferences. Return an empty updates list if none.\n\n"
            f"USER MESSAGE:\n{message}"
        ),
        expected_output="A PreferenceExtraction object with explicit preference updates only.",
        agent=agent,
        output_pydantic=PreferenceExtraction,
    )
    output = Crew(agents=[agent], tasks=[task], process=Process.sequential, verbose=False).kickoff()
    if output.pydantic is not None:
        extracted = output.pydantic
    elif output.json_dict is not None:
        extracted = PreferenceExtraction.model_validate(output.json_dict)
    else:
        raise ValueError("偏好提取未返回结构化结果")
    # A model-generated source cannot authorize a profile update unless it is a real quote.
    return [
        item for item in extracted.updates[:5]
        if item.source_quote.strip() in message
        and may_contain_durable_preference(item.source_quote)
        and not any(marker in item.source_quote.casefold() for marker in ONE_TRIP_MARKERS)
    ]


async def extract_explicit_preferences(message: str) -> list[PreferenceUpdate]:
    if not may_contain_durable_preference(message):
        return []
    return await asyncio.to_thread(_extract_sync, message)
