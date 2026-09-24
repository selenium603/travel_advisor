"""
Google Maps Directions API client for transport routes.
Docs: https://developers.google.com/maps/documentation/directions
"""

import logging
from backend.services.base import BaseAPIClient
from backend.config.settings import settings
from backend.models.schemas import TransportRoute
from typing import List

logger = logging.getLogger(__name__)


class GoogleMapsClient(BaseAPIClient):

    def __init__(self):
        super().__init__(base_url=settings.google_maps_base_url)

    async def get_directions(
        self,
        origin: str,
        destination: str,
        mode: str = "transit",
    ) -> List[TransportRoute]:
        """Get directions between two places.

        Args:
            mode: driving, transit, walking, or bicycling
        """
        if not settings.google_maps_api_key:
            logger.warning("Google Maps API key not configured")
            return []

        params = {
            "origin": origin,
            "destination": destination,
            "mode": mode,
            "alternatives": "true",
            "key": settings.google_maps_api_key,
            "language": "en",
        }

        data = await self._get("/json", params=params)
        if not data or data.get("status") != "OK":
            return []

        return self._parse_routes(data.get("routes", []), origin, destination, mode)

    def _parse_routes(self, routes: list, origin: str, destination: str, mode: str) -> List[TransportRoute]:
        results = []

        for route in routes[:3]:
            try:
                leg = route["legs"][0]
                steps = []
                for step in leg.get("steps", [])[:10]:
                    instruction = step.get("html_instructions", "")
                    # Strip HTML tags
                    import re
                    clean = re.sub(r"<[^>]+>", " ", instruction).strip()
                    if clean:
                        steps.append(f"{clean} ({step.get('distance', {}).get('text', '')})")

                fare = None
                if route.get("fare"):
                    fare = f"{route['fare'].get('text', '')}"

                results.append(TransportRoute(
                    mode=mode,
                    origin=origin,
                    destination=destination,
                    distance=leg.get("distance", {}).get("text", ""),
                    duration=leg.get("duration", {}).get("text", ""),
                    steps=steps,
                    fare=fare,
                ))
            except (KeyError, IndexError) as e:
                logger.warning(f"Failed to parse Google Maps route: {e}")
                continue

        return results
