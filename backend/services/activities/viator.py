"""
Viator API client for bookable tours and experiences.
Docs: https://docs.viator.com/partner-api/technical
"""

import logging
from typing import List, Optional
from backend.services.base import BaseAPIClient
from backend.config.settings import settings
from backend.models.schemas import ActivityOption

logger = logging.getLogger(__name__)


class ViatorClient(BaseAPIClient):

    def __init__(self):
        super().__init__(
            base_url=settings.viator_base_url,
            headers={
                "exp-api-key": settings.viator_api_key,
                "Accept": "application/json;version=2.0",
                "Content-Type": "application/json",
            },
        )

    async def _get_destination_id(self, city: str) -> Optional[str]:
        """Resolve city name to Viator destination ID."""
        data = await self._get("/search/freetext", params={"searchTerm": city})
        if not data:
            return None
        destinations = data.get("destinations", [])
        if destinations:
            return destinations[0].get("ref")
        return None

    async def search_experiences(
        self,
        destination: str,
        interests: List[str],
        max_results: int = 10,
    ) -> List[ActivityOption]:
        """Search Viator for tours and experiences."""
        if not settings.viator_api_key:
            logger.warning("Viator API key not configured")
            return []

        dest_id = await self._get_destination_id(destination)
        if not dest_id:
            logger.warning(f"Could not resolve Viator destination for: {destination}")
            return []

        # Build search tags from interests
        search_term = f"{', '.join(interests)} in {destination}"

        body = {
            "filtering": {
                "destination": dest_id,
            },
            "searchTerm": search_term,
            "pagination": {
                "start": 1,
                "count": max_results,
            },
            "currency": "USD",
        }

        data = await self._post("/search/products", json_body=body)
        if not data:
            return []

        return self._parse_results(data)

    def _parse_results(self, data: dict) -> List[ActivityOption]:
        results = []
        products = data.get("products", [])

        for product in products:
            try:
                pricing = product.get("pricing", {})
                price_from = pricing.get("summary", {}).get("fromPrice")
                if price_from is None:
                    price_from = pricing.get("fromPrice")

                duration = product.get("duration", {})
                duration_str = ""
                if duration.get("fixedDurationInMinutes"):
                    mins = duration["fixedDurationInMinutes"]
                    duration_str = f"{mins // 60}h {mins % 60}m" if mins >= 60 else f"{mins}m"
                elif duration.get("variableDurationFromMinutes"):
                    duration_str = f"{duration['variableDurationFromMinutes']}-{duration.get('variableDurationToMinutes', '')} min"

                reviews = product.get("reviews", {})
                rating = float(reviews.get("combinedAverageRating", 0))
                review_count = int(reviews.get("totalReviews", 0))

                images = product.get("images", [])
                image_url = images[0].get("variants", [{}])[0].get("url") if images else None

                results.append(ActivityOption(
                    provider="viator",
                    name=product.get("title", ""),
                    category="Tour / Experience",
                    description=product.get("description", "")[:200],
                    rating=rating,
                    review_count=review_count,
                    price=float(price_from) if price_from else None,
                    duration=duration_str,
                    image_url=image_url,
                    booking_url=f"https://www.viator.com/tours/{product.get('productCode', '')}",
                ))
            except (KeyError, ValueError, TypeError) as e:
                logger.warning(f"Failed to parse Viator product: {e}")
                continue

        return results
