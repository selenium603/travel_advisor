import unittest
from unittest.mock import AsyncMock, patch

from backend.config.settings import settings
from backend.services.flights.service import FlightService
from backend.services.wendao import WendaoClient


class FlightSearchTests(unittest.IsolatedAsyncioTestCase):
    async def test_wendao_query_keeps_route_and_dates_with_request_context(self):
        client = WendaoClient()
        client.query = AsyncMock(return_value="查询结果")
        await client.search_flights(
            "上海", "广州", "2099-10-10", "2099-10-14", 2, "economy",
            request_context="想去广州吃美食",
        )
        question = client.query.await_args.args[0]
        for detail in ("上海", "广州", "2099-10-10", "2099-10-14", "2位乘客", "想去广州吃美食"):
            self.assertIn(detail, question)

    async def test_generic_link_is_not_reported_as_verified_flight(self):
        service = FlightService()
        service.wendao.search_flights = AsyncMock(return_value="查看更多航班：https://example.com/search")
        with patch.object(settings, "wendao_api_key", "test-key"):
            result = await service.search("上海", "广州", "2099-10-10")
        self.assertIn("未返回可核实的具体航班报价", result.raw_response)
        self.assertEqual(result.source, "wendao")

    async def test_past_date_does_not_query_provider_or_claim_no_flights(self):
        service = FlightService()
        service.wendao.search_flights = AsyncMock()
        result = await service.search("上海", "广州", "2020-01-01")
        service.wendao.search_flights.assert_not_awaited()
        self.assertIn("日期已过去", result.raw_response)
        self.assertIn("不表示该航线没有航班", result.raw_response)


if __name__ == "__main__":
    unittest.main()
