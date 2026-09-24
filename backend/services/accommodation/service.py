"""
Accommodation service — uses Wendao when configured, then Booking.com and Airbnb.
"""

import asyncio
import logging
from typing import Optional
from backend.services.accommodation.booking import BookingClient
from backend.services.accommodation.airbnb import AirbnbClient
from backend.services.wendao import WendaoClient
from backend.config.settings import settings
from backend.models.schemas import AccommodationSearchResult

logger = logging.getLogger(__name__)


class AccommodationService:

    def __init__(self):
        self.booking = BookingClient()
        self.airbnb = AirbnbClient()
        self.wendao = WendaoClient()

    async def search(
        self,
        destination: str,
        check_in: str,
        check_out: str,
        guests: int = 2,
        request_context: Optional[str] = None,
    ) -> AccommodationSearchResult:
        """Search accommodation with the configured provider and existing fallbacks."""
        from datetime import datetime
        d1 = datetime.strptime(check_in, "%Y-%m-%d")
        d2 = datetime.strptime(check_out, "%Y-%m-%d")
        nights = (d2 - d1).days

        result = AccommodationSearchResult(
            destination=destination,
            check_in=check_in,
            check_out=check_out,
            nights=nights,
            guests=guests,
        )

        if settings.wendao_api_key:
            answer = await self.wendao.search_hotels(
                destination, check_in, check_out, guests, request_context=request_context
            )
            if answer:
                result.raw_response = answer
                result.source = "wendao"
                return result

        # Fetch from both providers in parallel
        logger.info(f"Searching accommodation in {destination}: {check_in} to {check_out}")
        booking_results, airbnb_results = await asyncio.gather(
            self.booking.search_hotels(destination, check_in, check_out, guests),
            self.airbnb.search_listings(destination, check_in, check_out, guests),
            return_exceptions=True,
        )

        options = []
        sources = []

        if isinstance(booking_results, list) and booking_results:
            options.extend(booking_results)
            sources.append("booking")
            logger.info(f"Booking.com returned {len(booking_results)} results")
        elif isinstance(booking_results, Exception):
            logger.error(f"Booking.com failed: {booking_results}")

        if isinstance(airbnb_results, list) and airbnb_results:
            options.extend(airbnb_results)
            sources.append("airbnb")
            logger.info(f"Airbnb returned {len(airbnb_results)} results")
        elif isinstance(airbnb_results, Exception):
            logger.error(f"Airbnb failed: {airbnb_results}")

        # Sort by rating descending, then price ascending
        options.sort(key=lambda x: (-x.rating, x.price_per_night))

        result.options = options
        result.source = " + ".join(sources) if sources else "none"

        if not options:
            logger.warning(f"No accommodation results for {destination}")

        return result
