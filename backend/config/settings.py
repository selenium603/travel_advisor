"""
Centralized configuration for all API keys and service settings.
"""

import os
from pathlib import Path
from dataclasses import dataclass, field
from dotenv import load_dotenv

load_dotenv()
os.environ.setdefault(
    "CREWAI_STORAGE_DIR",
    str(Path(__file__).resolve().parents[2] / "data" / "crewai"),
)


@dataclass
class Settings:
    # --- LLM ---
    gemini_api_key: str = field(default_factory=lambda: os.getenv("GEMINI_API_KEY", ""))
    openrouter_api_key: str = field(default_factory=lambda: os.getenv("OPENROUTER_API_KEY", ""))
    openrouter_model: str = field(default_factory=lambda: os.getenv("OPENROUTER_MODEL", "google/gemini-2.5-flash"))
    openrouter_embedding_model: str = field(default_factory=lambda: os.getenv("OPENROUTER_EMBEDDING_MODEL", "qwen/qwen3-embedding-4b"))
    wendao_api_key: str = field(default_factory=lambda: os.getenv("WENDAO_API_KEY", ""))

    # --- Flights ---
    amadeus_api_key: str = field(default_factory=lambda: os.getenv("AMADEUS_API_KEY", ""))
    amadeus_api_secret: str = field(default_factory=lambda: os.getenv("AMADEUS_API_SECRET", ""))
    serpapi_key: str = field(default_factory=lambda: os.getenv("SERPAPI_KEY", ""))

    # --- Accommodation ---
    booking_api_key: str = field(default_factory=lambda: os.getenv("BOOKING_API_KEY", ""))
    airbnb_api_key: str = field(default_factory=lambda: os.getenv("AIRBNB_API_KEY", ""))

    # --- Activities ---
    amap_api_key: str = field(default_factory=lambda: os.getenv("AMAP_API_KEY", ""))
    google_places_api_key: str = field(default_factory=lambda: os.getenv("GOOGLE_PLACES_API_KEY", ""))
    viator_api_key: str = field(default_factory=lambda: os.getenv("VIATOR_API_KEY", ""))
    yelp_api_key: str = field(default_factory=lambda: os.getenv("YELP_API_KEY", ""))

    # --- Logistics ---
    google_maps_api_key: str = field(default_factory=lambda: os.getenv("GOOGLE_MAPS_API_KEY", ""))
    openweather_api_key: str = field(default_factory=lambda: os.getenv("OPENWEATHER_API_KEY", ""))
    exchange_rate_api_key: str = field(default_factory=lambda: os.getenv("EXCHANGE_RATE_API_KEY", ""))

    # --- Service URLs ---
    amap_base_url: str = "https://restapi.amap.com"
    amadeus_base_url: str = "https://api.amadeus.com"
    serpapi_base_url: str = "https://serpapi.com"
    booking_base_url: str = "https://booking-com15.p.rapidapi.com/api/v1"
    airbnb_base_url: str = "https://airbnb19.p.rapidapi.com/api/v1"
    google_places_base_url: str = "https://maps.googleapis.com/maps/api/place"
    viator_base_url: str = "https://api.viator.com/partner"
    yelp_base_url: str = "https://api.yelp.com/v3"
    google_maps_base_url: str = "https://maps.googleapis.com/maps/api/directions"
    openweather_base_url: str = "https://api.openweathermap.org/data/2.5"
    exchange_rate_base_url: str = "https://api.exchangerate.host"
    rest_countries_base_url: str = "https://restcountries.com/v3.1"
    travelbriefing_base_url: str = "https://travelbriefing.org"

    # --- App ---
    cors_origins: list = field(default_factory=lambda: [
        "http://localhost:5173",
        "http://localhost:3000",
    ])


settings = Settings()
