# Multi-Agent AI Travel Planner v2.0

## What This System Does

**Input:**
```
Plan a 10-day luxury honeymoon to Italy focusing on food and history.
We want to visit Rome and Florence, staying in 5-star hotels.
```

**Output:**
- Complete day-by-day itinerary with real flight prices, real hotel options, real activities
- Restaurant recommendations, transport routes, weather forecasts
- Cultural tips, visa info, budget breakdown
- Booking links where available

## How It Works

3 AI agents handle reasoning. 4 API services fetch real-time data. AI only does analysis — travel data comes from 11 real APIs.

```
User Request
    |
[AI] Parse request --> structured params
    |
[APIs] Fetch in parallel (no AI):
    |-- Flights: Amadeus + SerpApi
    |-- Hotels: Booking.com + Airbnb
    |-- Activities: Google Places + Viator + Yelp
    |-- Logistics: Google Maps + Weather + Currency + Country info
    |
[AI] RAG knowledge (cultural tips, visa info)
    |
[AI] Compile final itinerary from real data
    |
Final Itinerary
```

## Get Started

```bash
# Install
pip install -r requirements.txt
cp .env.example .env
# Add your API keys to .env

# Run backend
uvicorn backend.app:app --host 0.0.0.0 --port 8000 --reload --reload-exclude "venv/*"

# Run frontend (separate terminal)
cd frontend && npm install && npm run dev
```

Open http://localhost:5173

## Documentation

| Doc | What it covers |
|-----|---------------|
| [QUICKSTART.md](QUICKSTART.md) | 5-minute setup guide |
| [README.md](README.md) | Full docs, all API keys, troubleshooting |
| [ARCHITECTURE.md](ARCHITECTURE.md) | System design, data flow, tech decisions |
| [FILE_STRUCTURE.md](FILE_STRUCTURE.md) | Complete file tree |
| [PROJECT_SUMMARY.md](PROJECT_SUMMARY.md) | High-level overview |

## Minimum API Keys Needed

1. `GEMINI_API_KEY` (paid plan required)
2. `AMADEUS_API_KEY` + `AMADEUS_API_SECRET` (free tier)
3. `GOOGLE_PLACES_API_KEY` (free credit)
4. `OPENWEATHER_API_KEY` (free)

See [README.md](README.md#api-keys-required) for the full list. Services skip gracefully if a key isn't configured.
