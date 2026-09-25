"""Connect request handling to short-term and long-term memory."""

import logging

from backend.memory.extractor import extract_explicit_preferences
from backend.memory.store import memory_store
from backend.models.schemas import TravelRequest


logger = logging.getLogger(__name__)


def _user_idea(request: TravelRequest) -> str:
    if request.trip_idea:
        return request.trip_idea.strip()
    text = request.message.split("\n\nEssential Details:", 1)[0]
    return text.removeprefix("Trip Request:").strip()


async def prepare_memory(request: TravelRequest) -> tuple[str, str | None]:
    """Remember the request, then apply only explicit durable profile updates."""
    if request.session_id:
        memory_store.record_request(request.session_id, _user_idea(request), request.form_details)
    warning = None
    try:
        for update in await extract_explicit_preferences(_user_idea(request)):
            memory_store.upsert_preference(update, "explicit_message", request.session_id)
    except Exception:
        logger.exception("Could not extract explicit travel preferences")
        warning = "长期偏好未能保存；本次行程仍会继续规划。"
    return memory_store.context(request.session_id), warning
