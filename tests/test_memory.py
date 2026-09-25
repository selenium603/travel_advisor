import json
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from backend.memory.extractor import _extract_sync, may_contain_durable_preference
from backend.memory.service import prepare_memory
from backend.memory.store import MemoryStore
from backend.models.schemas import PreferenceUpdate, TravelFormDetails, TravelPlanParams, TravelRequest


class MemoryStoreTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.path = Path(self.folder.name) / "memory.json"
        self.store = MemoryStore(self.path)

    def test_explicit_conflict_replaces_value_and_keeps_provenance(self):
        first = PreferenceUpdate(
            category="lodging", value="经济型酒店", source_quote="我喜欢经济型酒店"
        )
        latest = PreferenceUpdate(
            category="lodging", value="四五星酒店", source_quote="以后住宿我更喜欢四五星酒店"
        )
        self.store.upsert_preference(first, "explicit_message", "session-one")
        self.store.upsert_preference(latest, "explicit_message", "session-one")
        reopened = MemoryStore(self.path)
        profile = reopened.profile()
        self.assertEqual(profile["preferences"]["lodging"]["value"], "四五星酒店")
        self.assertEqual(profile["preferences"]["lodging"]["source"]["quote"], latest.source_quote)
        self.assertTrue(profile["preferences"]["lodging"]["updated_at"])
        self.assertEqual(profile["changes"][-1]["old_value"], "经济型酒店")
        self.assertEqual(profile["changes"][-1]["new_value"], "四五星酒店")
        self.assertEqual(len(json.loads(self.path.read_text(encoding="utf-8"))["profile"]), 1)

    def test_session_remembers_current_plan_and_bounded_messages(self):
        start = date.today() + timedelta(days=20)
        form = TravelFormDetails(
            origin="上海", departure_date=start, return_date=start + timedelta(days=4),
            travelers=2, budget_level="mid-range",
        )
        for index in range(12):
            self.store.record_request("session-one", f"想去巴黎第{index}次", form)
        self.assertEqual(len(self.store.session("session-one")["recent_messages"]), 8)
        params = TravelPlanParams(
            destinations=["巴黎"], destination_country="法国", origin="上海",
            departure_date=start, return_date=start + timedelta(days=4),
            duration_days=4, travelers=2, budget_level="mid-range",
        )
        self.store.record_params("session-one", params)
        self.store.record_state("session-one", "completed")
        session = MemoryStore(self.path).session("session-one")
        self.assertEqual(session["current_plan"]["travelers"], 2)
        self.assertEqual(session["current_plan_state"], "completed")
        self.assertEqual(session["recent_messages"][-1]["role"], "assistant")

    def test_delete_removes_active_preference(self):
        update = PreferenceUpdate(category="pace", value="不喜欢早起", source_quote="我不喜欢早起")
        self.store.upsert_preference(update, "explicit_message")
        self.assertTrue(self.store.delete_preference("pace"))
        self.assertNotIn("pace", self.store.profile()["preferences"])
        self.assertFalse(any(change["category"] == "pace" for change in self.store.profile()["changes"]))


class MemoryExtractionTests(unittest.IsolatedAsyncioTestCase):
    async def test_only_durable_wording_triggers_extraction(self):
        self.assertFalse(may_contain_durable_preference("这次去巴黎住四星级酒店"))
        self.assertTrue(may_contain_durable_preference("以后住宿我更喜欢四五星酒店"))

    async def test_request_update_is_available_to_same_plan(self):
        with tempfile.TemporaryDirectory() as folder:
            store = MemoryStore(Path(folder) / "memory.json")
            update = PreferenceUpdate(
                category="lodging", value="四五星酒店", source_quote="以后住宿我更喜欢四五星酒店"
            )
            with patch("backend.memory.service.memory_store", store), patch(
                "backend.memory.service.extract_explicit_preferences",
                new=AsyncMock(return_value=[update]),
            ):
                context, warning = await prepare_memory(TravelRequest(
                    message="以后住宿我更喜欢四五星酒店，去巴黎玩",
                    session_id="session-one",
                ))
            self.assertIsNone(warning)
            self.assertIn("四五星酒店", context)
            self.assertEqual(store.profile()["preferences"]["lodging"]["value"], "四五星酒店")

    async def test_model_quote_must_be_real_and_durable(self):
        message = "以后住宿我更喜欢四五星酒店，这次想吃粤菜"
        output = SimpleNamespace(pydantic=None, json_dict={"updates": [
            {"category": "lodging", "value": "四五星酒店", "source_quote": "以后住宿我更喜欢四五星酒店"},
            {"category": "food", "value": "粤菜", "source_quote": "这次想吃粤菜"},
            {"category": "pace", "value": "慢节奏", "source_quote": "我总是喜欢慢节奏"},
        ]})
        with patch("backend.memory.extractor.Agent"), patch("backend.memory.extractor.Task"), patch(
            "backend.memory.extractor.Crew", return_value=MagicMock(kickoff=MagicMock(return_value=output))
        ):
            updates = _extract_sync(message)
        self.assertEqual([(item.category, item.value) for item in updates], [("lodging", "四五星酒店")])

    async def test_extraction_failure_does_not_block_planning_context(self):
        with tempfile.TemporaryDirectory() as folder:
            store = MemoryStore(Path(folder) / "memory.json")
            with patch("backend.memory.service.memory_store", store), patch(
                "backend.memory.service.extract_explicit_preferences",
                new=AsyncMock(side_effect=RuntimeError("model unavailable")),
            ), patch("backend.memory.service.logger"):
                context, warning = await prepare_memory(TravelRequest(
                    message="以后我喜欢民宿，去巴黎", session_id="session-one",
                ))
            self.assertIn("recent_messages", context)
            self.assertIsNotNone(warning)
            self.assertEqual(store.profile()["preferences"], {})


if __name__ == "__main__":
    unittest.main()
