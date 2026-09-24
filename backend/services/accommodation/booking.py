"""
Booking.com API client via RapidAPI.
Docs: https://rapidapi.com/DataCrawler/api/booking-com15
"""

import logging
from typing import List, Optional
from backend.services.base import BaseAPIClient
from backend.config.settings import settings
from backend.models.schemas import AccommodationOption

logger = logging.getLogger(__name__)


class BookingClient(BaseAPIClient):

    def __init__(self):
        super().__init__(
            base_url=settings.booking_base_url,
            headers={
                "x-rapidapi-key": settings.booking_api_key,
                "x-rapidapi-host": "booking-com15.p.rapidapi.com",
            },
        )

    async def _get_destination_id(self, city: str) -> Optional[str]:
        """Resolve city name to Booking.com dest_id."""
        data = await self._get("/searchDestination", params={"query": city})
        if data and isinstance(data, list) and len(data) > 0:
            return data[0].get("dest_id")
        if data and isinstance(data, dict):
            items = data.get("data", [])
            if items:
                return items[0].get("dest_id")
        return None

    async def search_hotels(
        self,
        destination: str,
        check_in: str,
        check_out: str,
        guests: int = 2,
        rooms: int = 1,
    ) -> List[AccommodationOption]:
        """Search hotels via Booking.com RapidAPI."""
        if not settings.booking_api_key:
            logger.warning("Booking.com API key not configured")
            return []

        dest_id = await self._get_destination_id(destination)
        if not dest_id:
            logger.warning(f"Could not resolve destination ID for: {destination}")
            return []

        params = {
            "dest_id": dest_id,
            "search_type": "CITY",
            "arrival_date": check_in,
            "departure_date": check_out,
            "adults": guests,
            "room_qty": rooms,
            "page_number": 1,
            "units": "metric",
            "temperature_unit": "c",
            "languagecode": "en-us",
            "currency_code": "USD",
        }

        data = await self._get("/hotels/searchHotels", params=params)
        if not data or "data" not in data:
            return []

        return self._parse_results(data["data"], check_in, check_out)

    def _parse_results(self, data: dict, check_in: str, check_out: str) -> List[AccommodationOption]:
        results = []
        hotels = data.get("hotels", [])

        for hotel in hotels[:10]:
            try:
                property_info = hotel.get("property", {})
                price_info = property_info.get("priceBreakdown", {})
                gross = price_info.get("grossPrice", {})
                total = float(gross.get("value", 0))

                # Calculate nights
                from datetime import datetime
                d1 = datetime.strptime(check_in, "%Y-%m-%d")
                d2 = datetime.strptime(check_out, "%Y-%m-%d")
                nights = max((d2 - d1).days, 1)
                per_night = total / nights

                review_score = float(property_info.get("reviewScore", 0))
                # Booking uses 1-10 scale, normalize to 1-5
                rating = round(review_score / 2, 1) if review_score > 5 else review_score

                results.append(AccommodationOption(
                    provider="booking",
                    name=property_info.get("name", "Unknown"),
                    property_type=property_info.get("propertyClass", "Hotel"),
                    rating=rating,
                    review_count=int(property_info.get("reviewCount", 0)),
                    price_per_night=round(per_night, 2),
                    total_price=round(total, 2),
                    currency=gross.get("currency", "USD"),
                    neighborhood=property_info.get("wishlistName", ""),
                    distance_to_center_km=None,
                    amenities=[],
                    room_type="",
                    cancellation_policy=self._parse_cancellation(property_info),
                    breakfast_included="breakfast" in str(property_info).lower(),
                    image_url=property_info.get("photoUrls", [""])[0] if property_info.get("photoUrls") else None,
                ))
            except (KeyError, ValueError) as e:
                logger.warning(f"Failed to parse Booking.com hotel: {e}")
                continue

        return results

    def _parse_cancellation(self, prop: dict) -> str:
        if prop.get("isFreeCancellation"):
            return "Free cancellation"
        return "Non-refundable"
