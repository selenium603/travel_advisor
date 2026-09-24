"""
Flight service — uses Wendao when configured, then Amadeus and SerpApi.
"""

import logging
import re
from datetime import date
from typing import Optional
from backend.services.flights.amadeus import AmadeusClient
from backend.services.flights.serpapi import SerpApiFlightsClient
from backend.services.wendao import WendaoClient
from backend.config.settings import settings
from backend.models.schemas import FlightSearchResult

logger = logging.getLogger(__name__)


class FlightService:

    def __init__(self):
        self.amadeus = AmadeusClient()
        self.serpapi = SerpApiFlightsClient()
        self.wendao = WendaoClient()

    async def search(
        self,
        origin: str,
        destination: str,
        departure_date: str,
        return_date: Optional[str] = None,
        travelers: int = 1,
        cabin_class: str = "economy",
        request_context: Optional[str] = None,
    ) -> FlightSearchResult:
        """Search flights with the configured provider and existing fallbacks."""

        result = FlightSearchResult(
            origin=origin,
            destination=destination,
            departure_date=departure_date,
            return_date=return_date,
            travelers=travelers,
            cabin_class=cabin_class,
        )

        if date.fromisoformat(departure_date) < date.today():
            result.raw_response = (
                "出发日期已过去，无法核验当日可预订航班。"
                "这不表示该航线没有航班，请重新选择未来日期查询。"
            )
            result.source = "date_validation"
            return result

        if settings.wendao_api_key:
            answer = await self.wendao.search_flights(
                origin, destination, departure_date, return_date, travelers, cabin_class,
                request_context=request_context,
            )
            if answer:
                has_offer = bool(
                    re.search(r"(?:起飞|出发时间)\s*[：:]", answer)
                    and re.search(r"(?:价格|票价)\s*[：:]", answer)
                    and re.search(r"https?://", answer)
                )
                result.raw_response = answer if has_offer else (
                    "当前查询未返回可核实的具体航班报价；不能据此判断航线没有航班。\n\n"
                    f"服务商答复：{answer}"
                )
                result.source = "wendao"
                return result

        # Try Amadeus (primary)
        logger.info(f"Searching flights via Amadeus: {origin} -> {destination}")
        options = await self.amadeus.search_flights(
            origin=origin,
            destination=destination,
            departure_date=departure_date,
            return_date=return_date,
            travelers=travelers,
            cabin_class=cabin_class,
        )

        if options:
            result.options = options
            result.source = "amadeus"
            logger.info(f"Amadeus returned {len(options)} flight options")
            return result

        # Fallback to SerpApi
        logger.info("Amadeus returned no results, falling back to SerpApi")
        options = await self.serpapi.search_flights(
            origin=origin,
            destination=destination,
            departure_date=departure_date,
            return_date=return_date,
            travelers=travelers,
            cabin_class=cabin_class,
        )

        if options:
            result.options = options
            result.source = "serpapi"
            logger.info(f"SerpApi returned {len(options)} flight options")
        else:
            logger.warning(f"No flight results from any provider for {origin} -> {destination}")

        return result
