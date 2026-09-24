"""AMap Web Service client for places, directions, and weather in China."""

import asyncio
import logging
from typing import List, Optional

from backend.config.settings import settings
from backend.models.schemas import ActivityOption, TransportRoute, WeatherForecast
from backend.services.base import BaseAPIClient

logger = logging.getLogger(__name__)

INTEREST_KEYWORDS = {
    "history": "历史景点",
    "art": "美术馆",
    "culture": "博物馆",
    "nature": "公园",
    "adventure": "户外景点",
    "shopping": "购物中心",
    "nightlife": "酒吧",
    "architecture": "建筑景点",
    "beach": "海滩",
    "music": "音乐厅",
}


def _text(value) -> str:
    return value.strip() if isinstance(value, str) else ""


def _number(value) -> Optional[float]:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _distance(value) -> str:
    meters = _number(value)
    if meters is None:
        return ""
    return f"{meters / 1000:.1f} km" if meters >= 1000 else f"{meters:.0f} m"


def _duration(value) -> str:
    seconds = _number(value)
    if seconds is None:
        return ""
    minutes = round(seconds / 60)
    return f"{minutes // 60} h {minutes % 60} min" if minutes >= 60 else f"{minutes} min"


class AmapClient(BaseAPIClient):
    def __init__(self):
        super().__init__(base_url=settings.amap_base_url, timeout=20.0)

    async def _request(self, endpoint: str, params: dict) -> Optional[dict]:
        if not settings.amap_api_key:
            return None
        data = await self._get(endpoint, params={**params, "key": settings.amap_api_key, "output": "JSON"})
        if not isinstance(data, dict) or str(data.get("status")) != "1":
            if isinstance(data, dict):
                logger.warning("AMap %s returned code %s", endpoint, data.get("infocode", "unknown"))
            return None
        return data

    async def geocode(self, place: str) -> Optional[dict]:
        if not place:
            return None
        data = await self._request("/v3/geocode/geo", {"address": place})
        geocodes = data.get("geocodes", []) if data else []
        for item in geocodes:
            if isinstance(item, dict) and _text(item.get("location")):
                return item
        return None

    async def search_places(
        self, destination: str, interests: List[str], kind: str = "attractions",
    ) -> List[ActivityOption]:
        if not settings.amap_api_key or not destination:
            return []

        if kind == "dining":
            keywords = ["餐厅"]
        else:
            keywords = [
                INTEREST_KEYWORDS.get(interest.lower(), interest)
                for interest in interests
                if interest.lower() not in {"food", "dining", "美食", "餐饮"}
            ][:3] or ["景点"]

        results = []
        seen = set()
        for keyword in keywords:
            params = {
                "keywords": keyword,
                "city": destination,
                "citylimit": "true",
                "extensions": "all",
                "offset": 10,
            }
            if kind == "dining":
                params["types"] = "050000"
            data = await self._request("/v3/place/text", params)
            for place in data.get("pois", []) if data else []:
                if not isinstance(place, dict):
                    continue
                name = _text(place.get("name"))
                identity = _text(place.get("id")) or name
                if not name or identity in seen:
                    continue
                seen.add(identity)
                details = place.get("biz_ext")
                details = details if isinstance(details, dict) else {}
                photos = place.get("photos")
                image_url = _text(photos[0].get("url")) if isinstance(photos, list) and photos and isinstance(photos[0], dict) else None
                rating = _number(details.get("rating")) or 0
                results.append(ActivityOption(
                    provider="amap",
                    name=name,
                    category="餐厅" if kind == "dining" else _text(place.get("type")) or keyword,
                    description=_text(place.get("type")),
                    rating=rating,
                    review_count=0,
                    price=_number(details.get("cost")) if kind == "dining" else None,
                    currency="CNY",
                    address=_text(place.get("address")),
                    image_url=image_url,
                ))
        results.sort(key=lambda option: -option.rating)
        return results[:10]

    async def get_forecast(self, city: str) -> List[WeatherForecast]:
        location = await self.geocode(city)
        if not location:
            return []
        adcode = _text(location.get("adcode"))
        if not adcode:
            return []
        data = await self._request("/v3/weather/weatherInfo", {"city": adcode, "extensions": "all"})
        forecasts = data.get("forecasts", []) if data else []
        results = []
        for forecast in forecasts:
            for day in forecast.get("casts", []):
                high = _number(day.get("daytemp"))
                low = _number(day.get("nighttemp"))
                if high is None or low is None:
                    continue
                daytime = _text(day.get("dayweather"))
                nighttime = _text(day.get("nightweather"))
                description = daytime if daytime == nighttime else f"{daytime} / {nighttime}"
                results.append(WeatherForecast(
                    date=_text(day.get("date")),
                    temperature_high=high,
                    temperature_low=low,
                    description=description,
                ))
        return results

    async def get_directions(
        self, origin: str, destination: str, mode: str = "transit",
    ) -> List[TransportRoute]:
        if not settings.amap_api_key or not origin or not destination or origin == destination:
            return []
        start, end = await asyncio.gather(self.geocode(origin), self.geocode(destination))
        if not start or not end:
            return []
        params = {"origin": start["location"], "destination": end["location"]}
        if mode == "transit":
            params["city"] = _text(start.get("citycode")) or _text(start.get("city")) or origin
            if start.get("citycode") != end.get("citycode"):
                params["cityd"] = _text(end.get("citycode")) or _text(end.get("city")) or destination
            endpoint = "/v3/direction/transit/integrated"
        elif mode == "driving":
            endpoint = "/v3/direction/driving"
        else:
            return []

        data = await self._request(endpoint, params)
        route = data.get("route", {}) if data else {}
        if not isinstance(route, dict):
            return []
        options = route.get("transits", []) if mode == "transit" else route.get("paths", [])
        results = []
        for option in options[:3]:
            if not isinstance(option, dict):
                continue
            steps = []
            if mode == "transit":
                total_meters = 0.0
                for segment in option.get("segments", []):
                    walking = segment.get("walking", {})
                    if isinstance(walking, dict):
                        total_meters += _number(walking.get("distance")) or 0
                    for step in walking.get("steps", [])[:3] if isinstance(walking, dict) else []:
                        instruction = _text(step.get("instruction"))
                        if instruction:
                            steps.append(instruction)
                    bus = segment.get("bus", {})
                    for line in bus.get("buslines", [])[:1] if isinstance(bus, dict) else []:
                        total_meters += _number(line.get("distance")) or 0
                        name = _text(line.get("name"))
                        if name:
                            steps.append(name)
                fare = _number(option.get("cost"))
                distance = _distance(total_meters) if total_meters else ""
            else:
                steps = [_text(step.get("instruction")) for step in option.get("steps", [])[:10]]
                steps = [step for step in steps if step]
                fare = _number(option.get("tolls"))
                distance = _distance(option.get("distance"))
            results.append(TransportRoute(
                provider="amap",
                mode=mode,
                origin=origin,
                destination=destination,
                distance=distance,
                duration=_duration(option.get("duration")),
                steps=steps,
                fare=f"¥{fare:g}" if fare and fare > 0 else None,
            ))
        return results
