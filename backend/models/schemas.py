"""
Normalized data models for all services.
These provide a consistent format regardless of which API provider returned the data.
"""

from pydantic import BaseModel, Field, field_validator
from typing import List, Literal, Optional
from datetime import date


# ── Flight Models ─────────────────────────────────────────────────────────────

class FlightSegment(BaseModel):
    airline: str
    flight_number: str
    departure_airport: str
    arrival_airport: str
    departure_time: str
    arrival_time: str
    duration: str
    cabin_class: str


class FlightOption(BaseModel):
    provider: str  # "amadeus" or "serpapi"
    segments: List[FlightSegment]
    total_duration: str
    layovers: int
    layover_cities: List[str] = []
    price_per_person: float
    total_price: float
    currency: str = "USD"
    baggage: str = ""
    booking_url: Optional[str] = None


class FlightSearchResult(BaseModel):
    origin: str
    destination: str
    departure_date: str
    return_date: Optional[str] = None
    travelers: int
    cabin_class: str
    options: List[FlightOption] = []
    source: str = ""  # which API provided the data
    raw_response: str = ""  # prose returned by providers such as Wendao


# ── Accommodation Models ──────────────────────────────────────────────────────

class AccommodationOption(BaseModel):
    provider: str  # "booking" or "airbnb"
    name: str
    property_type: str  # Hotel, Apartment, Villa, etc.
    rating: float
    review_count: int
    price_per_night: float
    total_price: float
    currency: str = "USD"
    neighborhood: str = ""
    distance_to_center_km: Optional[float] = None
    amenities: List[str] = []
    room_type: str = ""
    cancellation_policy: str = ""
    breakfast_included: bool = False
    image_url: Optional[str] = None
    booking_url: Optional[str] = None


class AccommodationSearchResult(BaseModel):
    destination: str
    check_in: str
    check_out: str
    nights: int
    guests: int
    options: List[AccommodationOption] = []
    source: str = ""
    raw_response: str = ""  # prose returned by providers such as Wendao


# ── Activity Models ───────────────────────────────────────────────────────────

class ActivityOption(BaseModel):
    provider: str  # "google_places", "viator", "yelp"
    name: str
    category: str
    description: str = ""
    rating: float
    review_count: int
    price: Optional[float] = None
    currency: str = "USD"
    duration: Optional[str] = None
    address: str = ""
    image_url: Optional[str] = None
    booking_url: Optional[str] = None
    opening_hours: Optional[str] = None


class ActivitySearchResult(BaseModel):
    destination: str
    interests: List[str]
    attractions: List[ActivityOption] = []  # from Google Places
    tours: List[ActivityOption] = []  # from Viator
    dining: List[ActivityOption] = []  # from Yelp


# ── Logistics Models ──────────────────────────────────────────────────────────

class TransportRoute(BaseModel):
    mode: str  # driving, transit, walking, bicycling
    origin: str
    destination: str
    distance: str
    duration: str
    steps: List[str] = []
    fare: Optional[str] = None
    provider: str = ""


class WeatherForecast(BaseModel):
    date: str
    temperature_high: float
    temperature_low: float
    description: str
    humidity: Optional[int] = None
    wind_speed: Optional[float] = None
    icon: str = ""


class CurrencyInfo(BaseModel):
    base_currency: str
    target_currency: str
    rate: float
    last_updated: str = ""


class CountryInfo(BaseModel):
    name: str
    capital: str
    currency_name: str
    currency_code: str
    languages: List[str]
    timezone: str = ""
    calling_code: str = ""
    visa_info: str = ""
    vaccinations: str = ""
    safety_info: str = ""
    electricity: str = ""
    tipping_culture: str = ""


class LogisticsResult(BaseModel):
    routes: List[TransportRoute] = []
    weather: List[WeatherForecast] = []
    currency: Optional[CurrencyInfo] = None
    country: Optional[CountryInfo] = None


# ── Request Models ────────────────────────────────────────────────────────────

class TravelFormDetails(BaseModel):
    """Values explicitly entered in the trip form; these override inferred values."""

    origin: str
    departure_date: date
    return_date: date
    travelers: int = Field(ge=1, le=20)
    budget_level: Literal["budget", "mid-range", "luxury", "ultra-luxury"]
    interests: List[str] = Field(default_factory=list)
    traveler_details: str = ""
    special_requirements: str = ""


class TravelRequest(BaseModel):
    message: str
    form_details: Optional[TravelFormDetails] = None
    session_id: Optional[str] = Field(default=None, max_length=100)
    trip_idea: Optional[str] = Field(default=None, max_length=2000)


PreferenceCategory = Literal["lodging", "food", "pace", "sights", "budget"]


class PreferenceUpdate(BaseModel):
    category: PreferenceCategory
    value: str = Field(min_length=1, max_length=300)
    source_quote: str = Field(min_length=1, max_length=500)


class PreferenceExtraction(BaseModel):
    updates: List[PreferenceUpdate] = Field(default_factory=list)


class PreferenceEdit(BaseModel):
    value: str = Field(min_length=1, max_length=300)


class PreferenceMessage(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    session_id: Optional[str] = Field(default=None, max_length=100)


class TravelPlanParams(BaseModel):
    """Structured planning output before any external travel API is called."""

    destinations: List[str] = Field(min_length=1)
    destination_country: str
    origin: str
    departure_date: date
    return_date: date
    duration_days: int = Field(ge=1, le=90)
    travelers: int = Field(ge=1, le=20)
    budget_level: Literal["budget", "mid-range", "luxury", "ultra-luxury"]
    interests: List[str] = Field(default_factory=list)
    cabin_class: Literal["economy", "premium_economy", "business", "first"] = "economy"
    special_requirements: List[str] = Field(default_factory=list)

    @field_validator("destinations")
    @classmethod
    def clean_destinations(cls, cities: List[str]) -> List[str]:
        cleaned = list(dict.fromkeys(city.strip() for city in cities if city.strip()))
        if not cleaned:
            raise ValueError("At least one destination city is required")
        return cleaned

    @field_validator("origin", "destination_country")
    @classmethod
    def require_location(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("A city of origin and the first destination's country are required")
        return value


# ── Response Models ───────────────────────────────────────────────────────────

class ItineraryResponse(BaseModel):
    id: str
    request: str
    itinerary: str
    created_at: str
    status: str
