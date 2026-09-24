"""
Country information clients.
- REST Countries API (free): basic country data
- Travelbriefing.org (free): visa, vaccinations, safety
"""

import logging
from typing import Optional
from backend.services.base import BaseAPIClient
from backend.config.settings import settings
from backend.models.schemas import CountryInfo

logger = logging.getLogger(__name__)


class CountryInfoClient:
    """Combines REST Countries + Travelbriefing APIs."""

    def __init__(self):
        self.rest_countries = BaseAPIClient(base_url=settings.rest_countries_base_url)
        self.travelbriefing = BaseAPIClient(base_url=settings.travelbriefing_base_url)

    async def get_country_info(self, country_name: str) -> Optional[CountryInfo]:
        """Get comprehensive country information from multiple sources."""

        # Fetch from REST Countries
        base_info = await self._get_rest_countries(country_name)
        if not base_info:
            return None

        # Enrich with Travelbriefing data
        travel_info = await self._get_travelbriefing(country_name)
        if travel_info:
            base_info.visa_info = travel_info.get("visa", "")
            base_info.vaccinations = travel_info.get("vaccinations", "")
            base_info.safety_info = travel_info.get("safety", "")
            base_info.electricity = travel_info.get("electricity", "")

        return base_info

    async def _get_rest_countries(self, country_name: str) -> Optional[CountryInfo]:
        """Get basic country data from REST Countries API."""
        data = await self.rest_countries._get(f"/name/{country_name}")
        if not data or not isinstance(data, list) or len(data) == 0:
            return None

        country = data[0]
        try:
            # Extract currency info
            currencies = country.get("currencies", {})
            currency_code = ""
            currency_name = ""
            if currencies:
                code = list(currencies.keys())[0]
                currency_code = code
                currency_name = currencies[code].get("name", "")

            # Extract languages
            languages = list(country.get("languages", {}).values())

            # Extract timezone
            timezones = country.get("timezones", [])
            timezone = timezones[0] if timezones else ""

            # Extract calling code
            idd = country.get("idd", {})
            root = idd.get("root", "")
            suffixes = idd.get("suffixes", [""])
            calling_code = f"{root}{suffixes[0]}" if root else ""

            return CountryInfo(
                name=country.get("name", {}).get("common", country_name),
                capital=country.get("capital", [""])[0] if country.get("capital") else "",
                currency_name=currency_name,
                currency_code=currency_code,
                languages=languages,
                timezone=timezone,
                calling_code=calling_code,
            )
        except (KeyError, IndexError, TypeError) as e:
            logger.warning(f"Failed to parse REST Countries data: {e}")
            return None

    async def _get_travelbriefing(self, country_name: str) -> Optional[dict]:
        """Get travel-specific info from Travelbriefing.org."""
        data = await self.travelbriefing._get(f"/{country_name}", params={"format": "json"})
        if not data:
            return None

        result = {}
        try:
            # Visa info
            visa = data.get("visa", {})
            if visa:
                result["visa"] = visa.get("message", str(visa))

            # Vaccinations
            vaccinations = data.get("vaccinations", [])
            if vaccinations:
                vacc_list = [v.get("name", "") for v in vaccinations if v.get("name")]
                result["vaccinations"] = ", ".join(vacc_list)

            # Safety
            advisories = data.get("advisories", {})
            if advisories:
                score = advisories.get("score", "")
                result["safety"] = f"Advisory score: {score}" if score else ""

            # Electricity
            electricity = data.get("electricity", {})
            if electricity:
                voltage = electricity.get("voltage", "")
                frequency = electricity.get("frequency", "")
                plugs = electricity.get("plugs", [])
                plug_types = ", ".join([p.get("name", "") for p in plugs]) if isinstance(plugs, list) else str(plugs)
                result["electricity"] = f"{voltage}V, {frequency}Hz, Plug types: {plug_types}"

        except (KeyError, TypeError) as e:
            logger.warning(f"Failed to parse Travelbriefing data: {e}")

        return result
