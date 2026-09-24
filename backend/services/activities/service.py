"""
Activity service — combines Google Places, Viator, and Yelp results.
Separates results into attractions, tours/experiences, and dining.
"""

import asyncio
import logging
from backend.services.activities.google_places import GooglePlacesClient
from backend.services.activities.viator import ViatorClient
from backend.services.activities.yelp import YelpClient
from backend.services.amap import AmapClient
from backend.config.settings import settings
from backend.models.schemas import ActivitySearchResult
from typing import List

logger = logging.getLogger(__name__)


class ActivityService:

    def __init__(self):
        self.google_places = GooglePlacesClient()
        self.viator = ViatorClient()
        self.yelp = YelpClient()
        self.amap = AmapClient()

    async def search(
        self,
        destination: str,
        interests: List[str],
    ) -> ActivitySearchResult:
        """Search all providers in parallel, categorize results."""
        logger.info(f"Searching activities in {destination} for interests: {interests}")

        result = ActivitySearchResult(
            destination=destination,
            interests=interests,
        )

        amap_attractions, amap_dining = [], []
        if settings.amap_api_key:
            amap_attractions, amap_dining = await asyncio.gather(
                self.amap.search_places(destination, interests),
                self.amap.search_places(destination, interests, kind="dining"),
                return_exceptions=True,
            )
            if isinstance(amap_attractions, Exception):
                logger.error("AMap attraction search failed: %s", amap_attractions)
                amap_attractions = []
            if isinstance(amap_dining, Exception):
                logger.error("AMap dining search failed: %s", amap_dining)
                amap_dining = []

        places_results, viator_results, yelp_results = await asyncio.gather(
            self.google_places.search_places(destination, interests) if not amap_attractions else asyncio.sleep(0, result=[]),
            self.viator.search_experiences(destination, interests),
            self.yelp.search_businesses(destination, interests) if not amap_dining else asyncio.sleep(0, result=[]),
            return_exceptions=True,
        )

        if amap_attractions:
            result.attractions = amap_attractions
            logger.info("AMap returned %s attractions", len(amap_attractions))
        elif isinstance(places_results, list):
            result.attractions = places_results
            logger.info(f"Google Places returned {len(places_results)} attractions")
        elif isinstance(places_results, Exception):
            logger.error(f"Google Places failed: {places_results}")

        if isinstance(viator_results, list):
            result.tours = viator_results
            logger.info(f"Viator returned {len(viator_results)} tours")
        elif isinstance(viator_results, Exception):
            logger.error(f"Viator failed: {viator_results}")

        if amap_dining:
            result.dining = amap_dining
            logger.info("AMap returned %s dining options", len(amap_dining))
        elif isinstance(yelp_results, list):
            result.dining = yelp_results
            logger.info(f"Yelp returned {len(yelp_results)} dining options")
        elif isinstance(yelp_results, Exception):
            logger.error(f"Yelp failed: {yelp_results}")

        return result
