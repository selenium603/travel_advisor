import unittest
from datetime import date, timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from backend.crew import orchestrator
from backend.crew.plan_params import PlanParamsError


class PlanRepairTests(unittest.IsolatedAsyncioTestCase):
    async def test_one_repair_recovers_valid_parameters(self):
        departure = date.today() + timedelta(days=20)
        valid = {
            "destinations": ["雷克雅未克"],
            "destination_country": "冰岛",
            "origin": "上海",
            "departure_date": departure.isoformat(),
            "return_date": (departure + timedelta(days=4)).isoformat(),
            "duration_days": 4,
            "travelers": 2,
            "budget_level": "mid-range",
        }
        invalid_output = SimpleNamespace(pydantic=None, json_dict={**valid, "travelers": 0}, raw="bad")
        repaired_output = SimpleNamespace(pydantic=None, json_dict=valid, raw="fixed")
        crews = [MagicMock(kickoff=MagicMock(return_value=item)) for item in (invalid_output, repaired_output)]
        with patch.object(orchestrator, "create_travel_manager"), patch.object(
            orchestrator, "create_parameter_repair_agent"
        ), patch.object(orchestrator, "create_planning_task"), patch.object(
            orchestrator, "create_repair_task"
        ), patch.object(orchestrator, "Crew", side_effect=crews) as crew_factory:
            params = await orchestrator._resolve_plan_params("去雷克雅未克", None)
        self.assertEqual(params.travelers, 2)
        self.assertEqual(crew_factory.call_count, 2)
        for crew in crews:
            crew.kickoff.assert_called_once()

    async def test_second_invalid_result_stops_after_one_repair(self):
        bad = SimpleNamespace(pydantic=None, json_dict={}, raw="{}")
        crews = [MagicMock(kickoff=MagicMock(return_value=bad)) for _ in range(2)]
        with patch.object(orchestrator, "create_travel_manager"), patch.object(
            orchestrator, "create_parameter_repair_agent"
        ), patch.object(orchestrator, "create_planning_task"), patch.object(
            orchestrator, "create_repair_task"
        ), patch.object(orchestrator, "Crew", side_effect=crews) as crew_factory:
            with self.assertRaisesRegex(PlanParamsError, "修复后仍无效"):
                await orchestrator._resolve_plan_params("没有日期", None)
        self.assertEqual(crew_factory.call_count, 2)


if __name__ == "__main__":
    unittest.main()
