# Project Summary

## What This Is

A Multi-Agent AI Travel Planning system that combines real-time API data with AI-powered analysis. Unlike v1 which used 7 AI agents with mock data, v2 uses only 3 AI agents for reasoning while 4 API services fetch real flights, hotels, activities, and logistics data.

## Architecture at a Glance

| Component | Count | Purpose |
|-----------|-------|---------|
| AI Agents | 3 | Parse requests, provide knowledge, compile itineraries |
| API Services | 4 | Flights, accommodation, activities, logistics |
| External APIs | 11 | Amadeus, SerpApi, Booking.com, Airbnb, Google Places, Viator, Yelp, Google Maps, OpenWeatherMap, Exchange Rate, REST Countries |
| RAG Knowledge Base | 1 | ChromaDB with travel documents |
| LLM Calls per request | 2-3 | Down from ~15-20 in v1 |

## The 3 AI Agents

1. **Travel Planning Manager** — Parses natural language requests into structured parameters
2. **Travel Knowledge Expert** — Queries RAG for cultural tips, visa info, practical advice
3. **Itinerary Compiler** — Synthesizes all real API data into a day-by-day plan

## The 4 API Services

1. **Flight Service** — Amadeus (primary) + SerpApi (fallback)
2. **Accommodation Service** — Booking.com + Airbnb in parallel
3. **Activity Service** — Google Places + Viator + Yelp in parallel
4. **Logistics Service** — Google Maps + Weather + Currency + Country info in parallel

## Tech Stack

| Layer | Technology |
|-------|-----------|
| LLM | Google Gemini 2.0 Flash (via LiteLLM) |
| Agent Framework | CrewAI |
| HTTP Client | httpx (async) |
| Backend | FastAPI + Uvicorn |
| Frontend | React + Vite |
| Vector DB | ChromaDB |
| Data Models | Pydantic |

## What Changed from v1

| Aspect | v1 | v2 |
|--------|-----|-----|
| AI Agents | 7 (all using LLM) | 3 (reasoning only) |
| Data Source | Mock/random data | 11 real APIs |
| LLM Calls | ~15-20 per request | 2-3 per request |
| API Fetching | Sequential via LLM | Parallel via asyncio |
| Folder Structure | Flat (agents/, tools/) | Modular (backend/services/, backend/agents/) |
| Flight Data | Random prices | Real Amadeus/Google Flights data |
| Hotel Data | Random names | Real Booking.com/Airbnb listings |
| Activity Data | Random activities | Real Google Places/Viator/Yelp results |

## How to Run

```bash
# Backend
uvicorn backend.app:app --port 8000 --reload --reload-exclude "venv/*"

# Frontend
cd frontend && npm run dev
```

See [QUICKSTART.md](QUICKSTART.md) for full setup.

## Key Files

| File | Purpose |
|------|---------|
| `backend/crew/orchestrator.py` | Main pipeline — the heart of the system |
| `backend/config/settings.py` | All API keys and configuration |
| `backend/models/schemas.py` | Normalized data models |
| `backend/services/*/service.py` | Service coordinators |
| `backend/agents/definitions.py` | AI agent definitions |
| `main.py` | CLI entry point |
| `.env.example` | Required API keys template |

## Documentation

| Doc | Purpose |
|-----|---------|
| [START_HERE.md](START_HERE.md) | Entry point overview |
| [QUICKSTART.md](QUICKSTART.md) | 5-minute setup |
| [README.md](README.md) | Full documentation |
| [ARCHITECTURE.md](ARCHITECTURE.md) | System design |
| [FILE_STRUCTURE.md](FILE_STRUCTURE.md) | File tree |
