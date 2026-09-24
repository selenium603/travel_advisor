"""
Amadeus API client for flight search.
Docs: https://developers.amadeus.com/self-service/category/flights/api-doc/flight-offers-search
"""

import logging
from typing import List, Optional
from backend.services.base import BaseAPIClient
from backend.config.settings import settings
from backend.models.schemas import FlightOption, FlightSegment

logger = logging.getLogger(__name__)


class AmadeusClient(BaseAPIClient):

    def __init__(self):
        super().__init__(base_url=settings.amadeus_base_url)
        self._access_token: Optional[str] = None

    async def _authenticate(self) -> bool:
        """Get OAuth2 access token from Amadeus."""
        if not settings.amadeus_api_key or not settings.amadeus_api_secret:
            logger.warning("Amadeus API credentials not configured")
            return False

        data = await self._post(
            "/v1/security/oauth2/token",
            data={
                "grant_type": "client_credentials",
                "client_id": settings.amadeus_api_key,
                "client_secret": settings.amadeus_api_secret,
            },
        )
        if data and "access_token" in data:
            self._access_token = data["access_token"]
            self.headers["Authorization"] = f"Bearer {self._access_token}"
            return True

        logger.error("Amadeus authentication failed")
        return False

    async def search_flights(
        self,
        origin: str,
        destination: str,
        departure_date: str,
        return_date: Optional[str] = None,
        travelers: int = 1,
        cabin_class: str = "ECONOMY",
    ) -> List[FlightOption]:
        """Search flights via Amadeus Flight Offers Search API."""
        if not self._access_token:
            authenticated = await self._authenticate()
            if not authenticated:
                return []

        cabin_map = {
            "economy": "ECONOMY",
            "premium_economy": "PREMIUM_ECONOMY",
            "business": "BUSINESS",
            "first": "FIRST",
        }
        cabin = cabin_map.get(cabin_class.lower(), "ECONOMY")

        params = {
            "originLocationCode": origin.upper(),
            "destinationLocationCode": destination.upper(),
            "departureDate": departure_date,
            "adults": travelers,
            "travelClass": cabin,
            "max": 10,
            "currencyCode": "USD",
        }
        if return_date:
            params["returnDate"] = return_date

        data = await self._get("/v2/shopping/flight-offers", params=params)
        if not data or "data" not in data:
            return []

        return self._parse_offers(data["data"], travelers)

    def _parse_offers(self, offers: list, travelers: int) -> List[FlightOption]:
        results = []
        for offer in offers:
            try:
                segments = []
                layover_cities = []
                total_duration = ""

                for itinerary in offer.get("itineraries", []):
                    total_duration = itinerary.get("duration", "").replace("PT", "")
                    for seg in itinerary.get("segments", []):
                        segments.append(FlightSegment(
                            airline=seg.get("carrierCode", ""),
                            flight_number=f"{seg.get('carrierCode', '')}{seg.get('number', '')}",
                            departure_airport=seg["departure"]["iataCode"],
                            arrival_airport=seg["arrival"]["iataCode"],
                            departure_time=seg["departure"].get("at", ""),
                            arrival_time=seg["arrival"].get("at", ""),
                            duration=seg.get("duration", "").replace("PT", ""),
                            cabin_class=offer.get("travelerPricings", [{}])[0]
                                .get("fareDetailsBySegment", [{}])[0]
                                .get("cabin", "ECONOMY"),
                        ))
                        # Collect layover cities (intermediate stops)
                        if len(segments) > 1:
                            layover_cities.append(segments[-2].arrival_airport)

                price_info = offer.get("price", {})
                price_total = float(price_info.get("grandTotal", 0))
                price_per = price_total / travelers if travelers > 0 else price_total

                results.append(FlightOption(
                    provider="amadeus",
                    segments=segments,
                    total_duration=total_duration,
                    layovers=max(0, len(segments) - 1),
                    layover_cities=layover_cities,
                    price_per_person=round(price_per, 2),
                    total_price=round(price_total, 2),
                    currency=price_info.get("currency", "USD"),
                    baggage=self._extract_baggage(offer),
                ))
            except (KeyError, IndexError, ValueError) as e:
                logger.warning(f"Failed to parse Amadeus offer: {e}")
                continue

        return results

    def _extract_baggage(self, offer: dict) -> str:
        try:
            detail = offer["travelerPricings"][0]["fareDetailsBySegment"][0]
            bags = detail.get("includedCheckedBags", {})
            if bags.get("weight"):
                return f"{bags['weight']}{bags.get('weightUnit', 'KG')} checked bag included"
            if bags.get("quantity"):
                return f"{bags['quantity']} checked bag(s) included"
        except (KeyError, IndexError):
            pass
        return "Carry-on only"
