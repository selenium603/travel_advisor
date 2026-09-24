import unittest
from unittest.mock import AsyncMock, patch

from backend.config.settings import settings
from backend.services.amap import AmapClient


class AmapClientTests(unittest.IsolatedAsyncioTestCase):
    async def test_place_fields_keep_missing_data_missing(self):
        client = AmapClient()
        client._request = AsyncMock(return_value={
            "pois": [{
                "id": "B001",
                "name": "上海美术馆",
                "type": "文化场馆",
                "address": [],
                "biz_ext": {"rating": "4.7", "cost": "60"},
                "photos": [{"url": "https://example.com/photo.jpg"}],
            }],
        })
        with patch.object(settings, "amap_api_key", "test-key"):
            places = await client.search_places("上海", ["art"])

        self.assertEqual(len(places), 1)
        self.assertEqual(places[0].provider, "amap")
        self.assertEqual(places[0].rating, 4.7)
        self.assertEqual(places[0].address, "")
        self.assertIsNone(places[0].price)  # POI spending is not a ticket price.

    async def test_weather_uses_adcode_without_inventing_humidity_or_wind(self):
        client = AmapClient()

        async def response(endpoint, params):
            if endpoint == "/v3/geocode/geo":
                return {"geocodes": [{"location": "121.47,31.23", "adcode": "310000"}]}
            self.assertEqual(params["city"], "310000")
            return {"forecasts": [{"casts": [{
                "date": "2026-09-25", "daytemp": "28", "nighttemp": "21",
                "dayweather": "晴", "nightweather": "多云",
            }]}]}

        client._request = AsyncMock(side_effect=response)
        with patch.object(settings, "amap_api_key", "test-key"):
            weather = await client.get_forecast("上海")

        self.assertEqual(len(weather), 1)
        self.assertEqual(weather[0].temperature_high, 28)
        self.assertIsNone(weather[0].humidity)
        self.assertIsNone(weather[0].wind_speed)

    async def test_transit_route_maps_distance_duration_and_lines(self):
        client = AmapClient()

        async def geocode(place):
            return {
                "location": "121.47,31.23" if place == "起点" else "121.49,31.24",
                "citycode": "021",
            }

        client.geocode = AsyncMock(side_effect=geocode)
        client._request = AsyncMock(return_value={"route": {"transits": [{
            "cost": "4", "duration": "1800",
            "segments": [{
                "walking": {"distance": "500", "steps": [{"instruction": "步行到车站"}]},
                "bus": {"buslines": [{"name": "地铁2号线", "distance": "5500"}]},
            }],
        }]}})
        with patch.object(settings, "amap_api_key", "test-key"):
            routes = await client.get_directions("起点", "终点", "transit")

        self.assertEqual(len(routes), 1)
        self.assertEqual(routes[0].distance, "6.0 km")
        self.assertEqual(routes[0].duration, "30 min")
        self.assertEqual(routes[0].fare, "¥4")
        self.assertIn("地铁2号线", routes[0].steps)


if __name__ == "__main__":
    unittest.main()
