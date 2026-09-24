"""
Airbnb API client via RapidAPI.
Docs: https://rapidapi.com/3b-data-3b-data-default/api/airbnb19
"""

import logging
from typing import List, Optional
from backend.services.base import BaseAPIClient
from backend.config.settings import settings
from backend.models.schemas import AccommodationOption

logger = logging.getLogger(__name__)


class AirbnbClient(BaseAPIClient):

    def __init__(self):
        super().__init__(
            base_url=settings.airbnb_base_url,
            headers={
                "x-rapidapi-key": settings.airbnb_api_key,
                "x-rapidapi-host": "airbnb19.p.rapidapi.com",
            },
        )

    async def search_listings(
        self,
        destination: str,
        check_in: str,
        check_out: str,
        guests: int = 2,
    ) -> List[AccommodationOption]:
        """Search Airbnb listings via RapidAPI."""
        if not settings.airbnb_api_key:
            logger.warning("Airbnb API key not configured")
            return []

        params = {
            "location": destination,
            "checkin": check_in,
            "checkout": check_out,
            "adults": guests,
            "page": 1,
            "currency": "USD",
        }

        data = await self._get("/searchPropertyByPlace", params=params)
        if not data:
            return []

        return self._parse_results(data, check_in, check_out)

    def _parse_results(self, data: dict, check_in: str, check_out: str) -> List[AccommodationOption]:
        results = []
        listings = data.get("data", [])
        if isinstance(listings, dict):
            listings = listings.get("list", [])

        for listing in listings[:10]:
            try:
                info = listing.get("listing", listing)
                pricing = listing.get("pricingQuote", listing.get("pricing", {}))

                total_price = float(pricing.get("price", pricing.get("total", {}).get("amount", 0)))

                from datetime import datetime
                d1 = datetime.strptime(check_in, "%Y-%m-%d")
                d2 = datetime.strptime(check_out, "%Y-%m-%d")
                nights = max((d2 - d1).days, 1)
                per_night = total_price / nights

                results.append(AccommodationOption(
                    provider="airbnb",
                    name=info.get("name", info.get("title", "Airbnb Listing")),
                    property_type=info.get("roomTypeCategory", info.get("type", "Apartment")),
                    rating=float(info.get("avgRating", info.get("rating", 0))),
                    review_count=int(info.get("reviewsCount", info.get("reviews", 0))),
                    price_per_night=round(per_night, 2),
                    total_price=round(total_price, 2),
                    currency="USD",
                    neighborhood=info.get("neighborhood", ""),
                    amenities=info.get("previewAmenities", []) if isinstance(info.get("previewAmenities"), list) else [],
                    room_type=info.get("roomTypeCategory", ""),
                    image_url=info.get("contextualPictures", [{}])[0].get("picture") if info.get("contextualPictures") else None,
                    booking_url=f"https://www.airbnb.com/rooms/{info.get('id', '')}" if info.get("id") else None,
                ))
            except (KeyError, ValueError, TypeError) as e:
                logger.warning(f"Failed to parse Airbnb listing: {e}")
                continue

        return results
