# Multi-Agent AI Travel Planner v2.0

An AI travel planning system that combines **real-time API data** with **AI-powered analysis** to create personalized travel itineraries. Built with CrewAI, featuring 11 external API integrations and RAG for travel knowledge.

## Key Concepts

- **3 AI Agents** handle reasoning: parsing requests, cultural knowledge, and itinerary compilation
- **4 API Services** fetch real-time data: flights, accommodation, activities, and logistics
- **RAG Knowledge Base** provides cultural tips, visa info, and practical advice via ChromaDB
- **AI only does analysis** — all travel data comes from real APIs, not hallucinated by the LLM

## Architecture

```
User Request
    |
[AI] Travel Planning Manager --- parses request into structured params
    |
[API] 4 services fetch in parallel (no AI, pure HTTP)
    |--- Flights: Amadeus + SerpApi (fallback)
    |--- Accommodation: Booking.com + Airbnb
    |--- Activities: Google Places + Viator + Yelp
    |--- Logistics: Google Maps + OpenWeatherMap + Currency + Country Info
    |
[AI] Travel Knowledge Expert --- RAG for cultural/visa/practical info
    |
[AI] Itinerary Compiler --- synthesizes ALL real data into day-by-day plan
    |
Final Itinerary (with real prices, real hotels, booking links)
```

## Quick Start

### Prerequisites

- Python 3.9+
- API keys (see [API Keys Required](#api-keys-required) below)

### Installation

```bash
# Clone the project
cd "Multi Agent AI Travel Agent"

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # macOS/Linux
# or: venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Set up environment
cp .env.example .env
# Edit .env and add your API keys
```

### Running

**Backend:**
```bash
uvicorn backend.app:app --host 0.0.0.0 --port 8000 --reload --reload-exclude "venv/*" --reload-exclude "data/*"
```

**Frontend** (separate terminal):
```bash
cd frontend
npm install
npm run dev
```

**CLI mode** (no frontend needed):
```bash
python main.py
```

## API Keys Required

### Required
| Key | Purpose | Get it from |
|-----|---------|-------------|
| `OPENROUTER_API_KEY` or `GEMINI_API_KEY` | AI agents; OpenRouter takes precedence | [openrouter.ai](https://openrouter.ai/), [aistudio.google.com/apikey](https://aistudio.google.com/apikey) |

`OPENROUTER_MODEL` selects the OpenRouter model (default: `google/gemini-2.5-flash`).
Choose a model that supports tool calling. The same `OPENROUTER_API_KEY` also powers
the local knowledge base. `OPENROUTER_EMBEDDING_MODEL` defaults to
`qwen/qwen3-embedding-4b`; no OpenAI key is needed.

### Ctrip Wendao

Set `WENDAO_API_KEY` in `.env` to use [Wendao travel search](https://clawhub.ai/trips-ai/skills/wendao-skill)
for flights and hotels. Its natural-language answer is passed to the itinerary
compiler as source text; it is not parsed into the structured price fields.
If Wendao fails, the existing flight and hotel providers remain fallbacks.
Attractions, routes, and weather can use AMap as described below.

### AMap Web Service

Set `AMAP_API_KEY` in `.env` to use AMap for attractions, restaurants, routes,
and weather. Create a **Web Service API** key in the
[AMap developer console](https://lbs.amap.com/api/webservice/gettingstarted).
AMap is tried first; existing Google Places, Yelp, Google Maps, and OpenWeather
clients remain fallbacks when configured. AMap's standard weather response only
covers today and the next two days, and its overseas Web Services require
separate authorization. The project also requests transit routes between the
first few attractions returned by AMap.

### Flight APIs (need at least one)
| Key | Purpose | Get it from |
|-----|---------|-------------|
| `AMADEUS_API_KEY` + `AMADEUS_API_SECRET` | Primary flight search | [developers.amadeus.com](https://developers.amadeus.com/) |
| `SERPAPI_KEY` | Fallback flight search | [serpapi.com](https://serpapi.com/) |

### Accommodation APIs (need at least one)
| Key | Purpose | Get it from |
|-----|---------|-------------|
| `BOOKING_API_KEY` | Hotels (Booking.com via RapidAPI) | [rapidapi.com](https://rapidapi.com/DataCrawler/api/booking-com15) |
| `AIRBNB_API_KEY` | Rentals (Airbnb via RapidAPI) | [rapidapi.com](https://rapidapi.com/3b-data-3b-data-default/api/airbnb19) |

### Activity APIs (need at least one)
| Key | Purpose | Get it from |
|-----|---------|-------------|
| `AMAP_API_KEY` | Attractions and restaurants in China | [lbs.amap.com](https://lbs.amap.com/api/webservice/gettingstarted) |
| `GOOGLE_PLACES_API_KEY` | Attractions & restaurants | [console.cloud.google.com](https://console.cloud.google.com/) |
| `VIATOR_API_KEY` | Bookable tours | [docs.viator.com](https://docs.viator.com/) |
| `YELP_API_KEY` | Dining (5,000 calls/day free) | [yelp.com/developers](https://www.yelp.com/developers/) |

### Logistics APIs (all free)
| Key | Purpose | Get it from |
|-----|---------|-------------|
| `AMAP_API_KEY` | Routes and short weather forecast in China | [lbs.amap.com](https://lbs.amap.com/api/webservice/gettingstarted) |
| `GOOGLE_MAPS_API_KEY` | Transport routes | [console.cloud.google.com](https://console.cloud.google.com/) |
| `OPENWEATHER_API_KEY` | Weather forecast | [openweathermap.org](https://openweathermap.org/api) |

### Optional
| Key | Purpose |
|-----|---------|
| `OPENROUTER_EMBEDDING_MODEL` | Optional RAG embedding model override; uses `OPENROUTER_API_KEY` |
| `EXCHANGE_RATE_API_KEY` | Currency rates (fallback uses free API without key) |

Services gracefully skip any provider whose key isn't configured.

## Project Structure

```
backend/
├── app.py                          # FastAPI entry point
├── config/
│   └── settings.py                 # All API keys & service URLs
├── api/
│   ├── routes.py                   # REST and SSE planning endpoints
│   └── websocket.py                # Legacy WebSocket endpoint
├── services/                       # Pure API calls, NO AI
│   ├── flights/
│   │   ├── amadeus.py              # Amadeus API (primary)
│   │   ├── serpapi.py              # SerpApi Google Flights (fallback)
│   │   └── service.py              # FlightService coordinator
│   ├── accommodation/
│   │   ├── booking.py              # Booking.com via RapidAPI
│   │   ├── airbnb.py              # Airbnb via RapidAPI
│   │   └── service.py             # AccommodationService coordinator
│   ├── activities/
│   │   ├── google_places.py        # Attractions & restaurants
│   │   ├── viator.py              # Bookable tours
│   │   ├── yelp.py                # Dining recommendations
│   │   └── service.py             # ActivityService coordinator
│   ├── logistics/
│   │   ├── google_maps.py         # Directions & routes
│   │   ├── weather.py             # OpenWeatherMap
│   │   ├── currency.py            # Exchange rates
│   │   ├── country_info.py        # REST Countries + Travelbriefing
│   │   └── service.py             # LogisticsService coordinator
│   └── knowledge/
│       └── rag.py                 # ChromaDB RAG
├── agents/                         # Only 3 AI agents
│   ├── llm.py                     # Gemini LLM factory
│   ├── definitions.py             # Travel Manager, Knowledge Expert, Compiler
│   ├── tasks.py                   # Task definitions
│   └── tools.py                   # CrewAI tool wrapper (RAG only)
├── crew/
│   └── orchestrator.py            # Main pipeline
├── models/
│   └── schemas.py                 # Normalized Pydantic models
frontend/                           # React + Vite UI
data/
├── travel_knowledge/              # RAG documents (.txt)
└── chroma_db/                     # Vector store (auto-generated)
main.py                             # CLI entry point
```

## How It Works

### The Pipeline (2-3 AI calls instead of 15-20)

1. **AI Step 1** — Travel Manager parses natural language into structured parameters (destinations, dates, budget, interests)
2. **API Step** — 4 services fetch real data in parallel via `asyncio.gather` (flights, hotels, activities, logistics) — pure HTTP, no AI
3. **AI Step 2** — Knowledge Expert queries RAG for cultural/visa/practical info
4. **AI Step 3** — Itinerary Compiler takes ALL real API data + knowledge and creates a personalized day-by-day plan

The web page sends a single `POST /api/plan/stream` request. Its SSE response carries
`started`, `agent_progress`, `delta`, `completed`, and `error` messages. The browser reads
the response with `ReadableStream` and `TextDecoder`, displays the final itinerary as
CrewAI generates it, and replaces the preview with the saved final result on completion.
The older WebSocket endpoint remains available for existing clients.

### Adding Travel Knowledge

Add UTF-8 `.txt` or text-based `.pdf` files to `data/travel_knowledge/` and restart the
backend. For a new Chinese city, start the filename with its city name and a separator,
for example `成都-旅游指南.txt` or `乌鲁木齐-景点.pdf`. `成都市旅游指南.txt` also works.
Existing Chinese and English aliases for Shanghai, Guangzhou, Paris, Italy, and Europe
remain supported. The city is learned from the filename and used to filter retrieval;
it is not guessed from arbitrary document text. The index is rebuilt when files or the
embedding model change. Scanned image PDFs need OCR first.

The Guangzhou route guide is indexed one complete route at a time, with district and
category information. A query that names a district can therefore infer its city from
the guide, even without saying “Guangzhou”. The inspected 2025 Shanghai overview keeps
selected travel, museum, and geography pages. Other text files and PDFs use headings
and paragraphs as answer units; overly long paragraphs are split at sentence boundaries.
PDF page numbers remain in source references. Short passages are used for retrieval,
then the complete paragraph or route is returned with its heading and source.
OpenRouter embeddings and BM25 rank candidates together. A missing city, weak topic
overlap, or low vector similarity returns no match.
The knowledge base is static and does not fetch live visa rules, prices, or opening hours.

Run `python -m tests.evaluate_rag` from the project root to check the included Shanghai,
Guangzhou, and no-answer cases against the configured embedding API.

## Tech Stack

- **CrewAI** — Multi-agent orchestration
- **Google Gemini** — LLM (via LiteLLM)
- **FastAPI** — REST + SSE API (legacy WebSocket endpoint retained)
- **httpx** — Async HTTP client for all API services
- **ChromaDB** — Vector database for RAG
- **React + Vite** — Frontend
- **Pydantic** — Data models and validation

## Troubleshooting

### "Rate limit error" / "429" / "RESOURCE_EXHAUSTED"
Your Gemini free tier quota is exhausted. Enable billing at [aistudio.google.com](https://aistudio.google.com/) or wait for daily reset.

### "API key expired"
Generate a new key at [aistudio.google.com/apikey](https://aistudio.google.com/apikey) and update `.env`.

### Server reloads during execution
Run with: `uvicorn backend.app:app --reload --reload-exclude "venv/*" --reload-exclude "data/*"`

### "ModuleNotFoundError"
Activate your venv and run: `pip install -r requirements.txt`

### ChromaDB errors
Delete `data/chroma_db/` and run again.

## License

MIT License — see [LICENSE](LICENSE) for details.
