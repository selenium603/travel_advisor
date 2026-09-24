import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from backend.api.itinerary_storage import load_itineraries, save_itineraries


class ItineraryStorageTests(unittest.TestCase):
    def test_completed_trip_survives_reload_and_delete(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "history.json"
            with patch("backend.api.itinerary_storage.HISTORY_FILE", path):
                trip = {
                    "id": "trip-1",
                    "request": "上海两日游",
                    "itinerary": "第一天：外滩",
                    "created_at": "2026-09-24T12:00:00",
                    "status": "completed",
                }
                save_itineraries({trip["id"]: trip})
                self.assertEqual(load_itineraries(), {"trip-1": trip})
                save_itineraries({})
                self.assertEqual(load_itineraries(), {})


if __name__ == "__main__":
    unittest.main()
