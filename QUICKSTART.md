# Quick Start Guide

Get the Multi-Agent AI Travel Planner running in 5 minutes.

## Step 1: Install Dependencies

```bash
cd "Multi Agent AI Travel Agent"
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Step 2: Configure API Keys

```bash
cp .env.example .env
```

Edit `.env` and add at minimum one AI model key:

```
OPENROUTER_API_KEY=your_openrouter_key # Or use GEMINI_API_KEY
OPENROUTER_MODEL=google/gemini-2.5-flash
OPENROUTER_EMBEDDING_MODEL=qwen/qwen3-embedding-4b # Optional; RAG uses the same OpenRouter key
WENDAO_API_KEY=your_wendao_token      # Flights and hotels via Ctrip Wendao
AMAP_API_KEY=your_amap_web_service_key # Places, routes, weather
```

Other data sources can be configured separately if needed:

```
AMADEUS_API_KEY=your_amadeus_key      # Free tier: 2,000 calls/month
AMADEUS_API_SECRET=your_amadeus_secret
GOOGLE_PLACES_API_KEY=your_google_key # $200/month free credit
OPENWEATHER_API_KEY=your_weather_key  # Free: 1,000 calls/day
```

See [README.md](README.md#api-keys-required) for the full list.

## Step 3: Run the Backend

```bash
uvicorn backend.app:app --host 0.0.0.0 --port 8000 --reload --reload-exclude "venv/*" --reload-exclude "data/*"
```

## Step 4: Run the Frontend

Open a new terminal:

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173 in your browser.

## Step 5: Plan a Trip

Type a request like:
```
Plan a 5-day trip to Paris for a solo traveler who loves art and food.
Mid-range budget around $200/day for accommodation.
```

## What Happens

1. **Travel Manager** (AI) parses your request
2. **API Services** fetch real flights, hotels, activities, weather in parallel
3. **Knowledge Expert** (AI + RAG) provides cultural tips
4. **Itinerary Compiler** (AI) creates your personalized day-by-day plan

## CLI Mode (No Frontend)

```bash
python main.py
```

Edit the `selected_request` in [main.py](main.py) to change the travel request.

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Rate limit / 429 error | Check the quota of the configured AI provider |
| API key expired | Get new key at [aistudio.google.com/apikey](https://aistudio.google.com/apikey) |
| Server keeps reloading | Add `--reload-exclude "venv/*"` to uvicorn command |
| ModuleNotFoundError | `source venv/bin/activate && pip install -r requirements.txt` |
| No flight/hotel results | Check that the relevant API keys are in `.env` |

## Next Steps

- [README.md](README.md) — Full documentation and all API key details
- [ARCHITECTURE.md](ARCHITECTURE.md) — System design and data flow
- [FILE_STRUCTURE.md](FILE_STRUCTURE.md) — Complete file tree explained
