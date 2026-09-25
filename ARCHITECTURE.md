# System Architecture

## Overview

The system uses a **hybrid architecture**: AI agents handle reasoning and synthesis, while external APIs provide real-time data. This reduces LLM calls from ~15-20 (old architecture) to 2-3, while producing itineraries based on real data instead of AI-generated approximations.

## Pipeline

```
                          User Request (natural language)
                                |
                    +-----------+-----------+
                    |   AI: Travel Manager  |
                    |   Parses request into |
                    |   structured params   |
                    +-----------+-----------+
                                |
              +-----------------+-----------------+
              |                 |                 |
    +---------+------+ +-------+-------+ +-------+--------+
    | FlightService  | | AccommodationS| | ActivityService |
    | Amadeus(pri)   | | Booking.com   | | Google Places   |
    | SerpApi(fall)  | | Airbnb        | | Viator + Yelp   |
    +---------+------+ +-------+-------+ +-------+--------+
              |                 |                 |
              |        +-------+-------+          |
              |        |LogisticsServ. |          |
              |        |Google Maps    |          |
              |        |Weather+Curr.  |          |
              |        |Country Info   |          |
              |        +-------+-------+          |
              |                 |                 |
              +-----------------+-----------------+
                                |
                    asyncio.gather (parallel)
                                |
                    +-----------+-----------+
                    | AI: Knowledge Expert  |
                    | RAG for cultural/visa |
                    +-----------+-----------+
                                |
                    +-----------+-----------+
                    | AI: Itinerary Compiler|
                    | Synthesizes all data  |
                    | into day-by-day plan  |
                    +-----------+-----------+
                                |
                         Final Itinerary
```

## Components

### AI Agents (3 total)

| Agent | Purpose | Tools |
|-------|---------|-------|
| Travel Planning Manager | Parse natural language into structured params | RAG |
| Travel Knowledge Expert | Cultural tips, visa info, practical advice | RAG |
| Itinerary Compiler | Synthesize all data into final plan | None |

All agents use **Gemini 2.0 Flash** via LiteLLM with exponential backoff retry.

### API Services (4 services, 11 APIs)

All services are **async** (httpx), fetch in **parallel** via `asyncio.gather`, and return **normalized Pydantic models** regardless of which provider returned the data.

#### Flight Service
- **Amadeus** (primary) — OAuth2 auth, Flight Offers Search API
- **SerpApi** (fallback) — Google Flights scraping
- Returns: `FlightSearchResult` with `FlightOption` list

#### Accommodation Service
- **Booking.com** (via RapidAPI) — Hotel search with pricing
- **Airbnb** (via RapidAPI) — Rental listings
- Fetches both in parallel, merges and sorts results
- Returns: `AccommodationSearchResult` with `AccommodationOption` list

#### Activity Service
- **Google Places** — Attractions, restaurants, POIs
- **Viator** — Bookable tours and experiences
- **Yelp Fusion** — Dining recommendations
- Returns: `ActivitySearchResult` with separate lists for attractions, tours, dining

#### Logistics Service
- **Google Maps Directions** — Transport routes (transit + driving)
- **OpenWeatherMap** — 5-day forecast
- **Exchange Rate API** — Currency conversion (free fallback available)
- **REST Countries + Travelbriefing** — Visa, language, electricity, safety
- Returns: `LogisticsResult` with routes, weather, currency, country info

### RAG Knowledge Base
- **ChromaDB** vector store with OpenAI embeddings
- Documents in `data/travel_knowledge/*.txt`
- Queried by Knowledge Expert agent during reasoning
- Provides information APIs don't cover: cultural etiquette, packing tips, local customs

## Data Flow

### 1. Request Parsing
```
User request + explicit form + user memory
    --> CrewAI structured output (TravelPlanParams)
    --> form overrides inferred values
    --> Pydantic and business validation
    --> at most one repair attempt
    --> external travel APIs
```

### Session and profile memory

`data/itineraries.json` remains the history of generated plans. `data/memory.json` is a
separate, local single-user memory store:

- **Short term:** A browser tab keeps a stable `session_id` in `sessionStorage`. The
  backend retains the last eight messages, the current plan state, and validated trip
  parameters. Up to 50 sessions are retained.
- **Long term:** One profile stores lodging, food, pace, sights, and budget preferences.
  Each entry has a value, `updated_at`, and its source. Explicit new preferences replace
  the value in the same category; `changes` records the old and new values.
- **Extraction:** A structured preference task runs only for wording that could state a
  durable preference. An update is accepted only when its source quote occurs verbatim
  in the user's message and itself expresses a durable preference. One-trip choices do
  not become profile preferences. If extraction fails, the trip still runs and the UI
  shows a warning. Users can inspect, edit, or delete entries in **My
  Travel Memory**.
- **Priority:** Current form > current trip request > long-term profile > prior session
  messages. Previous destinations, dates, and traveler counts never fill a new trip.
  Memory is passed to the planner, relevant provider searches, and itinerary compiler.

The profile is local to this app instance, not an authenticated multi-user account.

### 2. Parallel API Fetching (no AI)
```python
flights, hotels, activities, logistics = await asyncio.gather(
    flight_service.search(...),
    accommodation_service.search(...),
    activity_service.search(...),
    logistics_service.get_logistics(...),
)
```

### 3. Data Normalization
Each service returns Pydantic models. Formatters convert them to readable text for the AI compiler.

### 4. AI Compilation
The compiler receives all real data as context and produces a personalized itinerary with actual prices, real hotel names, and booking links.

## Backend Architecture

```
backend/
├── config/settings.py      # Centralized config (dataclass)
├── models/schemas.py        # All Pydantic models
├── services/                # Pure HTTP, no AI
│   ├── base.py             # Shared httpx client
│   ├── flights/            # Amadeus + SerpApi
│   ├── accommodation/      # Booking + Airbnb
│   ├── activities/         # Places + Viator + Yelp
│   ├── logistics/          # Maps + Weather + Currency + Country
│   └── knowledge/          # ChromaDB RAG
├── agents/                  # AI layer
│   ├── llm.py             # Gemini factory
│   ├── definitions.py     # Planning, repair, knowledge, and compiler agents
│   ├── tasks.py           # Structured planning and itinerary tasks
│   └── tools.py           # CrewAI RAG tool wrapper
├── memory/                  # Session/profile store and preference extraction
├── crew/orchestrator.py     # Main pipeline
└── api/                     # FastAPI
    ├── routes.py           # REST endpoints
    └── websocket.py        # Real-time progress
```

## Key Design Decisions

### Why separate AI from data fetching?
- LLM calls are expensive and rate-limited; HTTP calls are cheap and fast
- Real API data is accurate; LLM-generated data can be hallucinated
- Parallel HTTP fetching is much faster than sequential LLM tool-calling

### Why async everywhere?
- 4 API services fetch in parallel via `asyncio.gather`
- Within each service, multiple providers fetch in parallel
- CrewAI's `kickoff()` is sync — wrapped in `run_in_executor` to avoid blocking FastAPI

### Why normalized models?
- `FlightOption`, `AccommodationOption`, etc. are provider-agnostic
- Adding a new provider means implementing one parser, not changing downstream code
- The AI compiler gets consistent data regardless of which API returned it

### Why fallback patterns?
- Flight: Amadeus (primary) --> SerpApi (fallback)
- Currency: exchangerate.host --> open.er-api.com (free, no key)
- Services return empty results instead of errors when keys aren't configured

## Performance

| Phase | Old (v1) | New (v2) |
|-------|----------|----------|
| LLM calls | ~15-20 | 2-3 |
| Data source | Mock/hallucinated | Real APIs |
| API fetching | Sequential via LLM | Parallel via asyncio |
| Total time | 90-120s | 30-60s (depends on API response) |

## Frontend Integration

The web page sends one `POST /api/plan/stream` request and reads its SSE response
with `ReadableStream` and `TextDecoder`. The backend sends progress updates with 4 steps:
1. `planning` — AI parsing request
2. `data_fetch` — APIs fetching real data
3. `knowledge` — RAG knowledge retrieval
4. `compilation` — AI building itinerary

During `compilation`, CrewAI text chunks are sent as `delta` events and rendered as
they arrive. A `completed` event carries the authoritative final itinerary, which is
saved to history. The earlier WebSocket endpoint remains available for older clients.
