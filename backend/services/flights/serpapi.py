"""
SerpApi Google Flights client (fallback).
Docs: https://serpapi.com/google-flights-api
"""

import logging
from typing import List, Optional
from backend.services.base import BaseAPIClient
from backend.config.settings import settings
from backend.models.schemas import FlightOption, FlightSegment

logger = logging.getLogger(__name__)


class SerpApiFlightsClient(BaseAPIClient):

    def __init__(self):
        super().__init__(base_url=settings.serpapi_base_url)

    async def search_flights(
        self,
        origin: str,
        destination: str,
        departure_date: str,
        return_date: Optional[str] = None,
        travelers: int = 1,
        cabin_class: str = "economy",
    ) -> List[FlightOption]:
        """Search flights via SerpApi Google Flights engine."""
        if not settings.serpapi_key:
            logger.warning("SerpApi key not configured")
            return []

        cabin_map = {"economy": "1", "premium_economy": "2", "business": "3", "first": "4"}

        params = {
            "engine": "google_flights",
            "api_key": settings.serpapi_key,
            "departure_id": origin.upper(),
            "arrival_id": destination.upper(),
            "outbound_date": departure_date,
            "adults": travelers,
            "travel_class": cabin_map.get(cabin_class.lower(), "1"),
            "currency": "USD",
            "hl": "en",
        }
        if return_date:
            params["return_date"] = return_date

        data = await self._get("/search.json", params=params)
        if not data:
            return []

        return self._parse_results(data, travelers, cabin_class)

    def _parse_results(self, data: dict, travelers: int, cabin_class: str) -> List[FlightOption]:
        results = []

        # SerpApi returns best_flights and other_flights
        all_flights = data.get("best_flights", []) + data.get("other_flights", [])

        for flight_group in all_flights[:10]:
            try:
                segments = []
                layover_cities = []

                for leg in flight_group.get("flights", []):
                    segments.append(FlightSegment(
                        airline=leg.get("airline", ""),
                        flight_number=f"{leg.get('airline', '')} {leg.get('flight_number', '')}",
                        departure_airport=leg.get("departure_airport", {}).get("id", ""),
                        arrival_airport=leg.get("arrival_airport", {}).get("id", ""),
                        departure_time=leg.get("departure_airport", {}).get("time", ""),
                        arrival_time=leg.get("arrival_airport", {}).get("time", ""),
                        duration=f"{leg.get('duration', 0)} min",
                        cabin_class=cabin_class,
                    ))

                # Layovers from SerpApi
                for layover in flight_group.get("layovers", []):
                    layover_cities.append(layover.get("name", ""))

                total_duration = f"{flight_group.get('total_duration', 0)} min"
                price = float(flight_group.get("price", 0))

                results.append(FlightOption(
                    provider="serpapi",
                    segments=segments,
                    total_duration=total_duration,
                    layovers=len(flight_group.get("layovers", [])),
                    layover_cities=layover_cities,
                    price_per_person=round(price, 2),
                    total_price=round(price * travelers, 2),
                    currency="USD",
                    baggage=self._extract_baggage(flight_group),
                    booking_url=flight_group.get("booking_token", None),
                ))
            except (KeyError, ValueError) as e:
                logger.warning(f"Failed to parse SerpApi flight: {e}")
                continue

        return results

    def _extract_baggage(self, flight_group: dict) -> str:
        extensions = flight_group.get("extensions", [])
        for ext in extensions:
            if isinstance(ext, str) and "bag" in ext.lower():
                return ext
        return ""
