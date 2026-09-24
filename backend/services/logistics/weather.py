"""
OpenWeatherMap API client for weather forecasts.
Docs: https://openweathermap.org/forecast5
"""

import logging
from backend.services.base import BaseAPIClient
from backend.config.settings import settings
from backend.models.schemas import WeatherForecast
from typing import List

logger = logging.getLogger(__name__)


class WeatherClient(BaseAPIClient):

    def __init__(self):
        super().__init__(base_url=settings.openweather_base_url)

    async def get_forecast(self, city: str) -> List[WeatherForecast]:
        """Get 5-day weather forecast for a city."""
        if not settings.openweather_api_key:
            logger.warning("OpenWeatherMap API key not configured")
            return []

        params = {
            "q": city,
            "appid": settings.openweather_api_key,
            "units": "metric",
            "cnt": 40,  # 5 days × 8 intervals
        }

        data = await self._get("/forecast", params=params)
        if not data or "list" not in data:
            return []

        return self._parse_forecast(data["list"])

    def _parse_forecast(self, forecast_list: list) -> List[WeatherForecast]:
        # Group by date and take one reading per day (noon)
        daily = {}
        for entry in forecast_list:
            dt_txt = entry.get("dt_txt", "")
            date_str = dt_txt.split(" ")[0]

            if date_str not in daily:
                daily[date_str] = {"highs": [], "lows": [], "descs": [], "entry": None}

            main = entry.get("main", {})
            daily[date_str]["highs"].append(main.get("temp_max", 0))
            daily[date_str]["lows"].append(main.get("temp_min", 0))

            weather = entry.get("weather", [{}])[0]
            daily[date_str]["descs"].append(weather.get("description", ""))

            # Keep noon entry as representative
            if "12:00:00" in dt_txt:
                daily[date_str]["entry"] = entry

        results = []
        for date_str, info in sorted(daily.items()):
            entry = info["entry"] or {}
            main = entry.get("main", {})
            weather = entry.get("weather", [{}])[0] if entry else {}
            wind = entry.get("wind", {})

            results.append(WeatherForecast(
                date=date_str,
                temperature_high=round(max(info["highs"]), 1),
                temperature_low=round(min(info["lows"]), 1),
                description=weather.get("description", info["descs"][0] if info["descs"] else ""),
                humidity=main.get("humidity", 0),
                wind_speed=wind.get("speed", 0),
                icon=weather.get("icon", ""),
            ))

        return results
