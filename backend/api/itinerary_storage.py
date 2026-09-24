"""Small on-disk store for travel planning history."""

import json
import os
from pathlib import Path
from uuid import uuid4


HISTORY_FILE = Path(__file__).resolve().parents[2] / "data" / "itineraries.json"


def load_itineraries() -> dict:
    if not HISTORY_FILE.exists():
        return {}
    with HISTORY_FILE.open(encoding="utf-8") as stream:
        items = json.load(stream)
    if not isinstance(items, list):
        raise ValueError(f"Invalid itinerary history in {HISTORY_FILE}")
    return {item["id"]: item for item in items}


def save_itineraries(items: dict) -> None:
    HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    temporary = HISTORY_FILE.with_name(f"{HISTORY_FILE.name}.{uuid4().hex}.tmp")
    try:
        with temporary.open("w", encoding="utf-8") as stream:
            json.dump(list(items.values()), stream, ensure_ascii=False, indent=2)
        os.replace(temporary, HISTORY_FILE)
    finally:
        temporary.unlink(missing_ok=True)
