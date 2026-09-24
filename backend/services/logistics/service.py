"""
Logistics service — combines Google Maps, Weather, Currency, and Country info.
"""

import asyncio
import logging
from typing import Optional
from backend.services.logistics.google_maps import GoogleMapsClient
from backend.services.logistics.weather import WeatherClient
from backend.services.logistics.currency import CurrencyClient
from backend.services.logistics.country_info import CountryInfoClient
from backend.services.amap import AmapClient
from backend.config.settings import settings
from backend.models.schemas import LogisticsResult

logger = logging.getLogger(__name__)


class LogisticsService:

    def __init__(self):
        self.maps = GoogleMapsClient()
        self.weather = WeatherClient()
        self.currency = CurrencyClient()
        self.country = CountryInfoClient()
        self.amap = AmapClient()

    async def _weather(self, city: str):
        if settings.amap_api_key:
            forecast = await self.amap.get_forecast(city)
            if forecast:
                return forecast
        return await self.weather.get_forecast(city)

    async def _directions(self, origin: str, destination: str, mode: str):
        if settings.amap_api_key:
            routes = await self.amap.get_directions(origin, destination, mode)
            if routes:
                return routes
        return await self.maps.get_directions(origin, destination, mode)

    async def get_local_routes(self, city: str, place_names: list[str]):
        """Connect the first few attractions using local transit routes."""
        if not settings.amap_api_key:
            return []
        pairs = list(zip(place_names, place_names[1:]))[:2]
        def in_city(place: str) -> str:
            return place if city in place else f"{city}{place}"

        routes = await asyncio.gather(*(
            self.amap.get_directions(in_city(start), in_city(end), "transit")
            for start, end in pairs
        ), return_exceptions=True)
        return [route for group in routes if isinstance(group, list) for route in group[:1]]

    async def get_logistics(
        self,
        destination_city: str,
        destination_country: str,
        origin: Optional[str] = None,
        base_currency: str = "USD",
    ) -> LogisticsResult:
        """Fetch all logistics data in parallel."""
        logger.info(f"Fetching logistics for {destination_city}, {destination_country}")

        result = LogisticsResult()

        # Build parallel tasks
        tasks = {}

        # Weather for destination
        tasks["weather"] = self._weather(destination_city)

        # Country info
        tasks["country"] = self.country.get_country_info(destination_country)

        # Transport routes (if origin provided)
        if origin:
            tasks["routes_transit"] = self._directions(origin, destination_city, mode="transit")
            tasks["routes_driving"] = self._directions(origin, destination_city, mode="driving")

        # Execute all in parallel
        keys = list(tasks.keys())
        results = await asyncio.gather(*tasks.values(), return_exceptions=True)

        data = dict(zip(keys, results))

        # Weather
        if isinstance(data.get("weather"), list):
            result.weather = data["weather"]
            logger.info(f"Weather: {len(result.weather)} days of forecast")

        # Country
        if isinstance(data.get("country"), object) and not isinstance(data.get("country"), Exception):
            country_info = data["country"]
            if country_info:
                result.country = country_info
                # Get currency exchange rate based on country's currency
                if country_info.currency_code and country_info.currency_code != base_currency:
                    try:
                        result.currency = await self.currency.get_exchange_rate(
                            base_currency=base_currency,
                            target_currency=country_info.currency_code,
                        )
                    except Exception as e:
                        logger.error(f"Currency fetch failed: {e}")

        # Routes
        routes = []
        for key in ["routes_transit", "routes_driving"]:
            val = data.get(key)
            if isinstance(val, list):
                routes.extend(val)
        result.routes = routes
        if routes:
            logger.info(f"Routes: {len(routes)} transport options")

        return result
