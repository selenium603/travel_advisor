"""
REST API routes for the travel planner.
"""

import uuid
import asyncio
import logging
import json
from datetime import datetime

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from backend.models.schemas import (
    TravelRequest, PreferenceEdit, PreferenceMessage, PreferenceUpdate,
)
from backend.crew.orchestrator import run_travel_pipeline
from backend.api.websocket import AGENT_STEPS, itinerary_store
from backend.api.itinerary_storage import save_itineraries
from backend.config.settings import settings
from backend.memory.extractor import extract_explicit_preferences
from backend.memory.service import prepare_memory
from backend.memory.store import PREFERENCE_CATEGORIES, memory_store

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")


def _sse(message: dict) -> str:
    return f"data: {json.dumps(message, ensure_ascii=False)}\n\n"


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "ok",
        "gemini_key_configured": bool(settings.gemini_api_key),
        "openrouter_key_configured": bool(settings.openrouter_api_key),
        "wendao_key_configured": bool(settings.wendao_api_key),
        "amap_key_configured": bool(settings.amap_api_key),
        "amadeus_key_configured": bool(settings.amadeus_api_key),
        "serpapi_key_configured": bool(settings.serpapi_key),
    }


@router.get("/itineraries")
async def list_itineraries():
    """List all saved itineraries."""
    items = sorted(itinerary_store.values(), key=lambda x: x["created_at"], reverse=True)
    return {"itineraries": items}


@router.get("/itineraries/{itinerary_id}")
async def get_itinerary(itinerary_id: str):
    """Get a specific itinerary by ID."""
    item = itinerary_store.get(itinerary_id)
    if not item:
        raise HTTPException(status_code=404, detail="Itinerary not found")
    return item


@router.delete("/itineraries/{itinerary_id}")
async def delete_itinerary(itinerary_id: str):
    """Delete a specific itinerary."""
    if itinerary_id not in itinerary_store:
        raise HTTPException(status_code=404, detail="Itinerary not found")
    del itinerary_store[itinerary_id]
    save_itineraries(itinerary_store)
    return {"status": "deleted"}


@router.get("/memory/profile")
async def get_memory_profile():
    return memory_store.profile()


@router.get("/memory/sessions/{session_id}")
async def get_memory_session(session_id: str):
    return memory_store.session(session_id)


@router.delete("/memory/sessions/{session_id}")
async def clear_memory_session(session_id: str):
    return {"deleted": memory_store.clear_session(session_id)}


@router.put("/memory/preferences/{category}")
async def set_memory_preference(category: str, edit: PreferenceEdit):
    if category not in PREFERENCE_CATEGORIES:
        raise HTTPException(status_code=404, detail="未知偏好类别")
    update = PreferenceUpdate(category=category, value=edit.value, source_quote=edit.value)
    return memory_store.upsert_preference(update, "manual_edit")


@router.delete("/memory/preferences/{category}")
async def delete_memory_preference(category: str):
    if category not in PREFERENCE_CATEGORIES:
        raise HTTPException(status_code=404, detail="未知偏好类别")
    return {"deleted": memory_store.delete_preference(category)}


@router.post("/memory/preferences/extract")
async def remember_preference_message(request: PreferenceMessage):
    try:
        updates = await extract_explicit_preferences(request.message)
    except Exception as exc:
        logger.exception("Preference extraction failed")
        raise HTTPException(status_code=502, detail="暂时无法识别偏好，请稍后重试或手动填写。") from exc
    for update in updates:
        memory_store.upsert_preference(update, "explicit_message", request.session_id)
    return {"updates": [item.model_dump() for item in updates], **memory_store.profile()}


@router.post("/plan")
async def create_plan(request: TravelRequest):
    """REST endpoint for creating a travel plan (non-streaming)."""
    if not (settings.openrouter_api_key or settings.gemini_api_key):
        raise HTTPException(status_code=500, detail="OPENROUTER_API_KEY or GEMINI_API_KEY not configured")

    try:
        memory_context, memory_warning = await prepare_memory(request)
        async def save_params(params):
            if request.session_id:
                memory_store.record_params(request.session_id, params)
        result = await run_travel_pipeline(
            request.message, form_details=request.form_details,
            memory_context=memory_context, params_callback=save_params,
        )
        if request.session_id:
            memory_store.record_state(request.session_id, "completed")

        itinerary_id = str(uuid.uuid4())
        itinerary_store[itinerary_id] = {
            "id": itinerary_id,
            "request": request.message,
            "form_details": request.form_details.model_dump(mode="json") if request.form_details else None,
            "itinerary": result,
            "created_at": datetime.now().isoformat(),
            "status": "completed",
            "memory_warning": memory_warning,
        }
        save_itineraries(itinerary_store)
        return itinerary_store[itinerary_id]
    except Exception as e:
        if request.session_id:
            memory_store.record_state(request.session_id, "failed")
        logger.error(f"Plan creation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/plan/stream")
async def stream_plan(request: TravelRequest):
    """Stream progress and real compiler text over a single HTTP response."""
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="请填写旅行需求。")
    if not (settings.openrouter_api_key or settings.gemini_api_key):
        raise HTTPException(status_code=500, detail="OPENROUTER_API_KEY or GEMINI_API_KEY not configured")

    itinerary_id = str(uuid.uuid4())
    itinerary_store[itinerary_id] = {
        "id": itinerary_id,
        "request": request.message,
        "form_details": request.form_details.model_dump(mode="json") if request.form_details else None,
        "itinerary": "",
        "created_at": datetime.now().isoformat(),
        "status": "processing",
    }
    save_itineraries(itinerary_store)

    async def events():
        queue: asyncio.Queue[dict] = asyncio.Queue()
        connected = True

        async def send(message: dict) -> None:
            if connected:
                queue.put_nowait(message)

        async def progress(step_key: str, label: str, status: str) -> None:
            if request.session_id:
                memory_store.record_state(request.session_id, f"{step_key}_{status}")
            step_index = next((i for i, step in enumerate(AGENT_STEPS) if step["key"] == step_key), 0)
            await send({
                "type": "agent_progress",
                "agent_key": step_key,
                "agent_label": label,
                "description": AGENT_STEPS[step_index]["description"],
                "step": step_index + 1,
                "total_steps": len(AGENT_STEPS),
                "status": status,
            })

        async def produce() -> None:
            try:
                await progress("memory", "Travel Memory", "running")
                memory_context, memory_warning = await prepare_memory(request)
                await progress("memory", "Travel Memory", "completed")
                if memory_warning:
                    await send({"type": "memory_warning", "message": memory_warning})

                async def save_params(params):
                    if request.session_id:
                        memory_store.record_params(request.session_id, params)

                result = await run_travel_pipeline(
                    request.message, progress_callback=progress,
                    text_callback=lambda piece: send({"type": "delta", "text": piece}),
                    form_details=request.form_details,
                    memory_context=memory_context, params_callback=save_params,
                )
                if request.session_id:
                    memory_store.record_state(request.session_id, "completed")
                itinerary_store[itinerary_id]["itinerary"] = result
                itinerary_store[itinerary_id]["status"] = "completed"
                save_itineraries(itinerary_store)
                await send({"type": "completed", "itinerary_id": itinerary_id, "itinerary": result})
            except Exception as exc:
                if request.session_id:
                    memory_store.record_state(request.session_id, "failed")
                logger.error("Streaming plan failed: %s", exc, exc_info=True)
                itinerary_store[itinerary_id]["status"] = "failed"
                save_itineraries(itinerary_store)
                await send({"type": "error", "message": str(exc)})

        await send({"type": "started", "itinerary_id": itinerary_id, "agents": AGENT_STEPS})
        producer = asyncio.create_task(produce())
        try:
            while True:
                try:
                    message = await asyncio.wait_for(queue.get(), timeout=15)
                except asyncio.TimeoutError:
                    yield ": ping\n\n"
                    continue
                yield _sse(message)
                if message["type"] in {"completed", "error"}:
                    break
        finally:
            connected = False
            # Planning continues after a browser disconnect so history is saved.
            if producer.done():
                await producer

    return StreamingResponse(
        events(), media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
