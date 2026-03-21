# AutoInsight ✦

![CI](https://github.com/YOUR_USERNAME/autoinsight/actions/workflows/ci.yml/badge.svg)
![Coverage](https://codecov.io/gh/YOUR_USERNAME/autoinsight/branch/main/graph/badge.svg)
![Python](https://img.shields.io/badge/python-3.12-blue)
![License](https://img.shields.io/badge/license-MIT-green)

> **Upload any CSV. Get instant AI-powered insights.**
> Production-grade data analysis tool for non-technical users — backed by Claude.

---

## Architecture

```
autoinsight/
│
├── backend/
│   ├── main.py                   # FastAPI app: lifespan, CORS, rate limiter, error handlers
│   ├── routes/
│   │   └── api.py                # All API endpoints (async, session-scoped, rate-limited)
│   └── modules/
│       ├── data_processor.py     # CSV ingestion, stats, correlation, trend detection
│       ├── llm_engine.py         # Async Claude API calls with retry + structured output
│       ├── session_store.py      # Redis-backed session store (in-memory fallback)
│       └── cache.py              # LLM response cache keyed on summary hash
│
├── frontend/
│   └── app.py                    # Streamlit dashboard (session-aware, env-configurable)
│
├── tests/
│   ├── conftest.py               # Shared fixtures, env setup
│   ├── test_data_processor.py    # Unit tests: CSV loading, stats, correlations
│   ├── test_llm_engine.py        # Unit tests: API key, summary builder, retry logic
│   └── test_api_routes.py        # Integration tests: all endpoints via TestClient
│
├── sample_data/
│   ├── generate_sample.py        # Regenerate the demo CSV
│   └── sample_sales.csv          # 500-row retail sales demo dataset
│
├── .env.example                  # All configurable env vars documented
├── Dockerfile                    # Multi-stage: separate backend and frontend images
├── docker-compose.yml            # Redis + backend + frontend wired together
├── requirements.txt
├── pytest.ini
└── start.sh                      # Local dev launcher
```

---

## System Design

```
Browser (Streamlit)
      │  X-Session-Id header on every request
      ▼
FastAPI Backend  ──── SlowAPI rate limiter (per IP)
      │
      ├── POST /api/upload-data
      │     • 50 MB hard limit (checked at HTTP layer + data layer)
      │     • Content-type + extension validation
      │     • Creates Redis session, returns session_id
      │
      ├── GET  /api/analyze          (requires X-Session-Id)
      │     • Reads DataFrame from session store
      │     • Returns summary stats + 50-row preview
      │
      ├── POST /api/generate-insights (rate: 5/min per IP)
      │     • Checks insight cache (Redis/memory, keyed on summary hash)
      │     • On miss: calls Claude via llm_engine
      │     • tenacity: 4 retries, exponential backoff (2–30s)
      │     • Stores result in cache (TTL: 1hr)
      │
      └── POST /api/query            (rate: 10/min per IP)
            • NL question → Claude → structured JSON answer
            • Confidence + caveat fields returned

Session Store (Redis / in-memory fallback)
      • Per-session DataFrame stored as JSON split
      • TTL: 1 hour (configurable)
      • Fully isolated: user A cannot access user B's data

Insight Cache (Redis / in-memory LRU)
      • Key: SHA-256 of serialised summary dict (first 24 chars)
      • TTL: 1 hour (configurable)
      • Prevents duplicate LLM calls for identical datasets
```

---

## Quickstart

### Prerequisites

- Python ≥ 3.11
- Redis (optional — falls back to in-memory if unavailable)
- `ANTHROPIC_API_KEY` in your environment

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
```

### Local dev (no Docker)

```bash
cd autoinsight

# Install deps
pip install -r requirements.txt

# Copy and edit env config
cp .env.example .env

# Start Redis (optional but recommended)
docker run -d -p 6379:6379 redis:7-alpine

# Launch backend + frontend
./start.sh
```

Open **http://localhost:8501** — upload `sample_data/sample_sales.csv` to try it immediately.

### Docker Compose (production-like)

```bash
cp .env.example .env
# Edit .env — set ANTHROPIC_API_KEY

docker compose up --build
```

Services:
- Frontend → http://localhost:8501
- API → http://localhost:8000
- API docs → http://localhost:8000/docs

---

## API Reference

All endpoints except `/health` and `/api/upload-data` require an `X-Session-Id` header
returned by `POST /api/upload-data`.

| Method | Endpoint | Rate limit | Description |
|--------|----------|------------|-------------|
| `POST` | `/api/upload-data` | 10/min | Upload CSV, get `session_id` |
| `GET` | `/api/analyze` | 30/min | Summary stats + data preview |
| `POST` | `/api/generate-insights` | 5/min | LLM-generated insights (cached) |
| `POST` | `/api/query` | 10/min | Natural language Q&A |
| `DELETE` | `/api/session` | — | Explicitly delete session data |
| `GET` | `/health` | — | Health check + API key status |

### Workflow example

```bash
# 1. Upload
SESSION=$(curl -s -X POST http://localhost:8000/api/upload-data \
  -F "file=@sample_data/sample_sales.csv" | jq -r .session_id)

# 2. Analyse
curl -H "X-Session-Id: $SESSION" http://localhost:8000/api/analyze | jq .summary.shape

# 3. Insights
curl -s -X POST -H "X-Session-Id: $SESSION" \
  http://localhost:8000/api/generate-insights | jq .

# 4. Ask a question
curl -s -X POST -H "X-Session-Id: $SESSION" \
  -H "Content-Type: application/json" \
  -d '{"question": "Why are sales dropping?"}' \
  http://localhost:8000/api/query | jq .
```

---

## Running Tests

```bash
pytest                        # all 40 tests
pytest -v                     # verbose
pytest tests/test_api_routes.py   # one file
pytest -k "test_upload"       # by name pattern
```

Test coverage:
- `test_data_processor.py` — 15 unit tests: CSV loading, file limits, stats accuracy, edge cases
- `test_llm_engine.py`     — 12 unit tests: API key, summary builder, JSON parsing, retry logic
- `test_api_routes.py`     — 13 integration tests: all endpoints, error paths, cache behaviour

No real API calls are made in tests — httpx and session store are fully mocked.

---

## Environment Variables

See `.env.example` for the full reference. Key variables:

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `ANTHROPIC_API_KEY` | **Yes** | — | Your Anthropic API key |
| `REDIS_URL` | No | `redis://localhost:6379/0` | Redis connection (omit = memory fallback) |
| `ALLOWED_ORIGINS` | No | `http://localhost:8501` | CORS allowed origins (comma-separated) |
| `API_BASE_URL` | No | `http://localhost:8000/api` | Backend URL as seen by frontend |
| `SESSION_TTL_SECONDS` | No | `3600` | Session lifetime |
| `CACHE_TTL_SECONDS` | No | `3600` | Insight cache lifetime |
| `LOG_LEVEL` | No | `INFO` | `DEBUG\|INFO\|WARNING\|ERROR` |

---

## Sample Dataset

`sample_data/sample_sales.csv` — 500 rows of simulated retail data with:
- A deliberate declining sales trend (~30% drop over the period)
- Strong correlation between `discount_rate` and `units_sold`
- Declining `customer_satisfaction`
- ~3% missing values in `customer_satisfaction`, ~2% in `marketing_spend`

Regenerate it anytime: `python sample_data/generate_sample.py`

---

## Production Checklist

- [x] API key loaded from environment — never hardcoded
- [x] Per-session data isolation (Redis-backed)
- [x] 50 MB file size limit enforced at HTTP + data layer
- [x] Fully async routes — no blocking calls on event loop
- [x] Exponential backoff retry on LLM calls (4 attempts, 2–30s)
- [x] Rate limiting: 5/min on insights, 10/min on queries
- [x] CORS restricted to configured origins
- [x] LLM response caching keyed on summary hash
- [x] Structured JSON logging (stdout, compatible with log aggregators)
- [x] FastAPI lifespan for startup validation
- [x] Global exception handler — no raw tracebacks leak to clients
- [x] Docker multi-stage build + docker-compose with healthchecks
- [x] 40 tests, 0 warnings, all mocked (no live API calls in CI)
- [x] `.env.example` documents every configurable variable

---

## Screenshots

| Upload & KPI Row | AI Insights Cards | NL Query |
|---|---|---|
| ![upload](docs/screenshot_upload.png) | ![insights](docs/screenshot_insights.png) | ![query](docs/screenshot_query.png) |

> To add your own: run the app, upload `sample_data/sample_sales.csv`, take screenshots of each tab, and save them to `docs/`.

---

## Why This Architecture? (Interview Q&A)

**"Why Redis instead of a database?"**
Session data is short-lived (1 hr TTL) and needs fast key-value access — Redis fits perfectly. A relational DB would be overkill and slower for this pattern.

**"What happens if the Anthropic API goes down?"**
`tenacity` retries up to 4 times with exponential backoff (2–30s). After that, the route returns a clean 502 with a user-friendly message — no stack trace exposed.

**"How would you scale this to 10,000 concurrent users?"**
Redis is already shared across workers, rate limiting is in place, and `docker-compose` can scale `backend` replicas with `--scale backend=4`. The next bottleneck would be LLM throughput — solved by adding a job queue (Celery + Redis) for insight generation.

**"Why not send the raw CSV to the LLM?"**
Cost, latency, and privacy. A 10k-row CSV at ~50 bytes/row is 500KB — roughly 125k tokens. The summary is ~130 words. Same insights, 1000× cheaper and faster.

---

## License

MIT
