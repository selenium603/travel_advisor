import json
import sys
import types
import unittest
from unittest.mock import patch

stub = types.ModuleType("backend.crew.orchestrator")
stub.run_travel_pipeline = None
with patch.dict(sys.modules, {"backend.crew.orchestrator": stub}):
    from backend.api import routes
from backend.models.schemas import TravelFormDetails, TravelRequest


class PlanStreamTests(unittest.IsolatedAsyncioTestCase):
    async def test_sse_sends_live_text_and_persists_final_result(self):
        async def fake_pipeline(message, progress_callback, text_callback, form_details, memory_context, params_callback):
            self.assertEqual(message, "去成都旅行")
            self.assertIsNone(form_details)
            self.assertIn("long_term_preferences", memory_context)
            await progress_callback("compilation", "编排行程", "running")
            await text_callback("成都")
            await text_callback("行程")
            return "成都行程"

        with patch.object(routes.settings, "openrouter_api_key", "test-key"), patch.object(
            routes, "run_travel_pipeline", side_effect=fake_pipeline
        ), patch.object(routes, "save_itineraries"):
            response = await routes.stream_plan(TravelRequest(message="去成都旅行"))
            frames = [chunk async for chunk in response.body_iterator]

        messages = [json.loads(frame.removeprefix("data: ").strip()) for frame in frames]
        self.assertEqual([item["type"] for item in messages], [
            "started", "agent_progress", "agent_progress", "agent_progress",
            "delta", "delta", "completed",
        ])
        self.assertEqual("".join(item["text"] for item in messages if item["type"] == "delta"), "成都行程")
        itinerary_id = messages[0]["itinerary_id"]
        self.assertEqual(routes.itinerary_store[itinerary_id]["status"], "completed")
        self.assertEqual(routes.itinerary_store[itinerary_id]["itinerary"], "成都行程")
        routes.itinerary_store.pop(itinerary_id)

    async def test_sse_reports_failure_and_marks_history(self):
        async def fake_pipeline(*args, **kwargs):
            raise RuntimeError("规划失败")

        with patch.object(routes.settings, "openrouter_api_key", "test-key"), patch.object(
            routes, "run_travel_pipeline", side_effect=fake_pipeline
        ), patch.object(routes, "save_itineraries"), patch.object(routes.logger, "error"):
            response = await routes.stream_plan(TravelRequest(message="去成都旅行"))
            frames = [chunk async for chunk in response.body_iterator]

        messages = [json.loads(frame.removeprefix("data: ").strip()) for frame in frames]
        self.assertEqual([item["type"] for item in messages], [
            "started", "agent_progress", "agent_progress", "error",
        ])
        itinerary_id = messages[0]["itinerary_id"]
        self.assertEqual(routes.itinerary_store[itinerary_id]["status"], "failed")
        routes.itinerary_store.pop(itinerary_id)

    async def test_stream_passes_and_saves_explicit_form_details(self):
        form = TravelFormDetails(
            origin="上海", departure_date="2026-11-01", return_date="2026-11-05",
            travelers=2, budget_level="mid-range",
        )

        async def fake_pipeline(message, progress_callback, text_callback, form_details, memory_context, params_callback):
            self.assertEqual(message, "想一个人去巴黎玩")
            self.assertEqual(form_details.travelers, 2)
            return "行程"

        with patch.object(routes.settings, "openrouter_api_key", "test-key"), patch.object(
            routes, "run_travel_pipeline", side_effect=fake_pipeline
        ), patch.object(routes, "save_itineraries"):
            response = await routes.stream_plan(TravelRequest(message="想一个人去巴黎玩", form_details=form))
            frames = [chunk async for chunk in response.body_iterator]

        messages = [json.loads(frame.removeprefix("data: ").strip()) for frame in frames]
        itinerary_id = messages[0]["itinerary_id"]
        self.assertEqual(routes.itinerary_store[itinerary_id]["form_details"]["travelers"], 2)
        routes.itinerary_store.pop(itinerary_id)
