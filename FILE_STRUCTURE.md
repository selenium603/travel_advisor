# File Structure

```
Multi Agent AI Travel Agent/
|
|-- main.py                              CLI entry point
|-- setup.py                             Project setup script
|-- requirements.txt                     Python dependencies
|-- .env.example                         API key template
|-- .gitignore
|-- LICENSE
|
|-- backend/
|   |-- app.py                           FastAPI entry point
|   |
|   |-- config/
|   |   |-- settings.py                  All API keys, URLs, app config
|   |
|   |-- api/
|   |   |-- routes.py                    REST endpoints (/api/plan, /api/health, etc.)
|   |   |-- websocket.py                 WebSocket handler + progress updates
|   |
|   |-- models/
|   |   |-- schemas.py                   Normalized Pydantic models for all services
|   |
|   |-- services/                        Pure API calls — no AI
|   |   |-- base.py                      Shared async HTTP client (httpx)
|   |   |
|   |   |-- flights/
|   |   |   |-- amadeus.py               Amadeus Flight Offers API (primary)
|   |   |   |-- serpapi.py               SerpApi Google Flights (fallback)
|   |   |   |-- service.py               FlightService: primary + fallback logic
|   |   |
|   |   |-- accommodation/
|   |   |   |-- booking.py               Booking.com via RapidAPI
|   |   |   |-- airbnb.py               Airbnb via RapidAPI
|   |   |   |-- service.py              AccommodationService: merges both providers
|   |   |
|   |   |-- activities/
|   |   |   |-- google_places.py         Google Places API (attractions + restaurants)
|   |   |   |-- viator.py               Viator API (bookable tours)
|   |   |   |-- yelp.py                 Yelp Fusion API (dining)
|   |   |   |-- service.py              ActivityService: categorizes into attractions/tours/dining
|   |   |
|   |   |-- logistics/
|   |   |   |-- google_maps.py           Google Maps Directions API
|   |   |   |-- weather.py              OpenWeatherMap forecast
|   |   |   |-- currency.py             Exchange rate API
|   |   |   |-- country_info.py         REST Countries + Travelbriefing
|   |   |   |-- service.py              LogisticsService: combines all logistics data
|   |   |
|   |   |-- knowledge/
|   |       |-- rag.py                   ChromaDB RAG service
|   |
|   |-- agents/                          AI layer — only 3 agents
|   |   |-- llm.py                       Gemini LLM factory (LiteLLM + retry)
|   |   |-- definitions.py              Agent definitions (Manager, Knowledge, Compiler)
|   |   |-- tasks.py                    Task definitions for each agent
|   |   |-- tools.py                    CrewAI tool wrapper for RAG
|   |
|   |-- crew/
|       |-- orchestrator.py              Main pipeline: AI parse -> API fetch -> AI compile
|
|-- frontend/
|   |-- src/
|   |   |-- App.jsx                      Main app component
|   |   |-- components/
|   |   |   |-- AgentProgress.jsx        Pipeline progress display
|   |   |   |-- ChatInput.jsx            User input
|   |   |   |-- Header.jsx
|   |   |   |-- ItineraryDisplay.jsx     Itinerary rendering
|   |   |   |-- Sidebar.jsx             History sidebar
|   |   |   |-- TripDetailsForm.jsx      Trip details form
|   |   |   |-- WelcomeScreen.jsx
|   |   |-- hooks/
|   |       |-- useWebSocket.js          WebSocket connection
|   |       |-- useItineraryHistory.js   Local storage history
|   |-- package.json
|   |-- vite.config.js
|
|-- data/
|   |-- travel_knowledge/                RAG documents (.txt files)
|   |   |-- Europe.txt
|   |   |-- Italy.txt
|   |   |-- Paris.txt
|   |   |-- Packing.txt
|   |   |-- Luxury Travel.txt
|   |   |-- Honeymoon.txt
|   |
|   |-- chroma_db/                       Vector store (auto-generated)
|
|-- docs/
    |-- README.md                        Full documentation
    |-- QUICKSTART.md                    5-minute guide
    |-- START_HERE.md                    Entry point
    |-- ARCHITECTURE.md                  System design
    |-- FILE_STRUCTURE.md                This file
    |-- PROJECT_SUMMARY.md               High-level overview
```

## Key Files to Know

| Want to... | Look at... |
|------------|-----------|
| Run the system | `main.py` (CLI) or `backend/app.py` (API) |
| Understand the pipeline | `backend/crew/orchestrator.py` |
| See how APIs are called | `backend/services/*/` |
| Modify AI agents | `backend/agents/definitions.py` |
| Change API configuration | `backend/config/settings.py` |
| Add travel knowledge | `data/travel_knowledge/*.txt` |
| Understand data models | `backend/models/schemas.py` |

## Data Flow Through Files

```
User Request
    |
    v
backend/api/websocket.py          receives request
    |
    v
backend/crew/orchestrator.py      runs the pipeline
    |
    +-> backend/agents/definitions.py   AI: parse request
    |   backend/agents/tasks.py
    |
    +-> backend/services/flights/       API: search flights
    +-> backend/services/accommodation/ API: search hotels
    +-> backend/services/activities/    API: search activities
    +-> backend/services/logistics/     API: get logistics
    |       (all via backend/services/base.py HTTP client)
    |       (all return backend/models/schemas.py models)
    |
    +-> backend/agents/definitions.py   AI: RAG knowledge
    |   backend/services/knowledge/rag.py
    |
    +-> backend/agents/definitions.py   AI: compile itinerary
    |
    v
Final itinerary -> WebSocket -> Frontend
```
