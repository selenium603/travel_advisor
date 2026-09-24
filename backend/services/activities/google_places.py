"""
Google Places API client for attractions and restaurants.
Docs: https://developers.google.com/maps/documentation/places/web-service
"""

import logging
from typing import Dict, List, Optional
from backend.services.base import BaseAPIClient
from backend.config.settings import settings
from backend.models.schemas import ActivityOption

logger = logging.getLogger(__name__)

# Google Places type mappings for travel interests
INTEREST_TYPE_MAP = {
    "food": ["restaurant", "cafe", "bakery"],
    "history": ["museum", "church", "hindu_temple", "synagogue", "mosque"],
    "art": ["art_gallery", "museum"],
    "adventure": ["park", "amusement_park", "stadium"],
    "culture": ["museum", "library", "city_hall"],
    "nightlife": ["night_club", "bar"],
    "shopping": ["shopping_mall", "department_store"],
}


class GooglePlacesClient(BaseAPIClient):

    def __init__(self):
        super().__init__(base_url=settings.google_places_base_url)

    async def search_places(
        self,
        destination: str,
        interests: List[str],
        max_results: int = 10,
    ) -> List[ActivityOption]:
        """Search Google Places for attractions based on interests."""
        if not settings.google_places_api_key:
            logger.warning("Google Places API key not configured")
            return []

        all_results = []

        for interest in interests:
            place_types = INTEREST_TYPE_MAP.get(interest.lower(), ["tourist_attraction"])
            for place_type in place_types[:2]:  # Limit API calls per interest
                params = {
                    "query": f"{interest} in {destination}",
                    "type": place_type,
                    "key": settings.google_places_api_key,
                    "language": "en",
                }

                data = await self._get("/textsearch/json", params=params)
                if not data or data.get("status") != "OK":
                    continue

                for place in data.get("results", [])[:5]:
                    try:
                        photo_ref = ""
                        if place.get("photos"):
                            photo_ref = place["photos"][0].get("photo_reference", "")

                        image_url = None
                        if photo_ref:
                            image_url = (
                                f"{settings.google_places_base_url}/photo"
                                f"?maxwidth=400&photo_reference={photo_ref}"
                                f"&key={settings.google_places_api_key}"
                            )

                        option = ActivityOption(
                            provider="google_places",
                            name=place.get("name", ""),
                            category=interest.title(),
                            description=place.get("formatted_address", ""),
                            rating=float(place.get("rating", 0)),
                            review_count=int(place.get("user_ratings_total", 0)),
                            price=self._price_level_to_amount(place.get("price_level")),
                            address=place.get("formatted_address", ""),
                            image_url=image_url,
                            opening_hours=self._format_hours(place.get("opening_hours")),
                        )
                        all_results.append(option)
                    except (KeyError, ValueError) as e:
                        logger.warning(f"Failed to parse Google Place: {e}")
                        continue

        # Deduplicate by name
        seen = set()
        deduped = []
        for r in all_results:
            if r.name not in seen:
                seen.add(r.name)
                deduped.append(r)

        # Sort by rating
        deduped.sort(key=lambda x: -x.rating)
        return deduped[:max_results]

    def _price_level_to_amount(self, level) -> Optional[float]:
        if level is None:
            return None
        # Google's 0-4 scale to approximate USD
        return {0: 0, 1: 15, 2: 30, 3: 60, 4: 100}.get(level)

    def _format_hours(self, hours_data) -> Optional[str]:
        if not hours_data:
            return None
        if hours_data.get("open_now") is not None:
            return "Open now" if hours_data["open_now"] else "Closed"
        return None
