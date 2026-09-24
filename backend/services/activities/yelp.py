"""
Yelp Fusion API client for restaurants and dining.
Docs: https://docs.developer.yelp.com/docs/fusion-intro
"""

import logging
from backend.services.base import BaseAPIClient
from backend.config.settings import settings
from backend.models.schemas import ActivityOption
from typing import List

logger = logging.getLogger(__name__)

# Map interests to Yelp categories
INTEREST_CATEGORY_MAP = {
    "food": "restaurants,food",
    "nightlife": "nightlife,bars",
    "shopping": "shopping",
    "culture": "arts,museums",
}


class YelpClient(BaseAPIClient):

    def __init__(self):
        super().__init__(
            base_url=settings.yelp_base_url,
            headers={
                "Authorization": f"Bearer {settings.yelp_api_key}",
                "Accept": "application/json",
            },
        )

    async def search_businesses(
        self,
        destination: str,
        interests: List[str],
        max_results: int = 10,
    ) -> List[ActivityOption]:
        """Search Yelp for restaurants and local businesses."""
        if not settings.yelp_api_key:
            logger.warning("Yelp API key not configured")
            return []

        all_results = []

        # Determine Yelp categories from interests
        categories = set()
        for interest in interests:
            cat = INTEREST_CATEGORY_MAP.get(interest.lower())
            if cat:
                categories.add(cat)

        # Default to restaurants if no specific food-related interest
        if not categories:
            categories.add("restaurants,food")

        for category in categories:
            params = {
                "location": destination,
                "categories": category,
                "sort_by": "rating",
                "limit": max_results,
            }

            data = await self._get("/businesses/search", params=params)
            if not data or "businesses" not in data:
                continue

            for biz in data["businesses"]:
                try:
                    price_str = biz.get("price", "")
                    # Yelp uses $, $$, $$$, $$$$
                    price_estimate = len(price_str) * 20 if price_str else None

                    cats = [c.get("title", "") for c in biz.get("categories", [])]

                    all_results.append(ActivityOption(
                        provider="yelp",
                        name=biz.get("name", ""),
                        category=", ".join(cats) if cats else "Dining",
                        description=f"{price_str} - {', '.join(cats)}" if cats else "",
                        rating=float(biz.get("rating", 0)),
                        review_count=int(biz.get("review_count", 0)),
                        price=price_estimate,
                        address=", ".join(biz.get("location", {}).get("display_address", [])),
                        image_url=biz.get("image_url"),
                        booking_url=biz.get("url"),
                    ))
                except (KeyError, ValueError) as e:
                    logger.warning(f"Failed to parse Yelp business: {e}")
                    continue

        # Deduplicate and sort
        seen = set()
        deduped = []
        for r in all_results:
            if r.name not in seen:
                seen.add(r.name)
                deduped.append(r)

        deduped.sort(key=lambda x: (-x.rating, -x.review_count))
        return deduped[:max_results]
