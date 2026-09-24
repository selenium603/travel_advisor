"""
Exchange rate API client.
Uses exchangerate.host (free, no key required for basic usage)
and Fixer.io as alternative.
"""

import logging
from typing import Optional
from backend.services.base import BaseAPIClient
from backend.config.settings import settings
from backend.models.schemas import CurrencyInfo

logger = logging.getLogger(__name__)


class CurrencyClient(BaseAPIClient):

    def __init__(self):
        super().__init__(base_url=settings.exchange_rate_base_url)

    async def get_exchange_rate(
        self,
        base_currency: str = "USD",
        target_currency: str = "EUR",
    ) -> Optional[CurrencyInfo]:
        """Get exchange rate between two currencies."""
        params = {
            "base": base_currency.upper(),
            "symbols": target_currency.upper(),
        }

        if settings.exchange_rate_api_key:
            params["access_key"] = settings.exchange_rate_api_key

        data = await self._get("/latest", params=params)
        if not data:
            # Fallback to free API
            return await self._fallback_rate(base_currency, target_currency)

        rates = data.get("rates", {})
        rate = rates.get(target_currency.upper())

        if rate is None:
            return await self._fallback_rate(base_currency, target_currency)

        return CurrencyInfo(
            base_currency=base_currency.upper(),
            target_currency=target_currency.upper(),
            rate=round(float(rate), 4),
            last_updated=data.get("date", ""),
        )

    async def _fallback_rate(self, base: str, target: str) -> Optional[CurrencyInfo]:
        """Fallback to open.er-api.com (free, no key)."""
        try:
            from backend.services.base import BaseAPIClient
            client = BaseAPIClient(base_url="https://open.er-api.com")
            data = await client._get(f"/v6/latest/{base.upper()}")
            if data and "rates" in data:
                rate = data["rates"].get(target.upper())
                if rate:
                    return CurrencyInfo(
                        base_currency=base.upper(),
                        target_currency=target.upper(),
                        rate=round(float(rate), 4),
                        last_updated=data.get("time_last_update_utc", ""),
                    )
        except Exception as e:
            logger.error(f"Currency fallback failed: {e}")

        return None
