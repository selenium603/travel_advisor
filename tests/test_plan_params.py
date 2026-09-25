import unittest
from datetime import date, timedelta

from backend.crew.plan_params import PlanParamsError, validate_plan_params
from backend.models.schemas import TravelFormDetails


class PlanParamsTests(unittest.TestCase):
    def setUp(self):
        departure = date.today() + timedelta(days=30)
        self.proposed = {
            "destinations": ["雷克雅未克"],
            "destination_country": "冰岛",
            "origin": "上海",
            "departure_date": departure.isoformat(),
            "return_date": (departure + timedelta(days=5)).isoformat(),
            "duration_days": 5,
            "travelers": 1,
            "budget_level": "luxury",
            "interests": ["Nature & Wildlife"],
        }

    def test_city_outside_old_whitelist_is_accepted(self):
        params = validate_plan_params(self.proposed)
        self.assertEqual(params.destinations, ["雷克雅未克"])
        self.assertEqual(params.destination_country, "冰岛")

    def test_explicit_form_overrides_conflicting_prose_parameters(self):
        form = TravelFormDetails(
            origin="北京",
            departure_date=date.today() + timedelta(days=40),
            return_date=date.today() + timedelta(days=44),
            travelers=2,
            budget_level="budget",
            interests=["Food & Cuisine"],
            special_requirements="素食",
        )
        params = validate_plan_params(self.proposed, form)
        self.assertEqual(params.origin, "北京")
        self.assertEqual(params.travelers, 2)
        self.assertEqual(params.budget_level, "budget")
        self.assertEqual(params.duration_days, 4)
        self.assertEqual(params.interests, ["Food & Cuisine"])
        self.assertIn("素食", params.special_requirements)

    def test_invalid_dates_and_counts_are_rejected(self):
        invalid = dict(self.proposed, travelers=0)
        with self.assertRaises(PlanParamsError):
            validate_plan_params(invalid)
        invalid = dict(self.proposed, return_date=self.proposed["departure_date"])
        with self.assertRaises(PlanParamsError):
            validate_plan_params(invalid)
        invalid = dict(self.proposed, duration_days=9)
        with self.assertRaises(PlanParamsError):
            validate_plan_params(invalid)


if __name__ == "__main__":
    unittest.main()
