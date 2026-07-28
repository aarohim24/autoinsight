# AutoInsight

![CI](https://github.com/aarohim24/autoinsight/actions/workflows/ci.yml/badge.svg)
![Python](https://img.shields.io/badge/python-3.12-blue)
![License](https://img.shields.io/badge/license-MIT-green)

> **Upload any CSV. Get instant AI-powered insights.**
> Production-grade data analysis tool for non-technical users — backed by Groq API.

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
│       ├── llm_engine.py         # Async Groq API calls with retry + structured output
│       ├── session_store.py      # Redis-backed session store (in-memory fallback)
│       └── cache.py              # LLM response cache keyed on summary hash
│
├── frontend-next/
│   ├── app/                      # Next.js App Router (pages, API routes)
│   └── lib/                      # Client utilities (API, proxy helpers)
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
Browser (Next.js Frontend @ localhost:3000)
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
      │     • On miss: calls Groq API via llm_engine
      │     • tenacity: 4 retries, exponential backoff (2–30s)
      │     • Stores result in cache (TTL: 1hr)
      │
      └── POST /api/query            (rate: 10/min per IP)
            • NL question → Groq API → structured JSON answer
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
- `GROQ_API_KEY` in your environment (get free key at [console.groq.com](https://console.groq.com))

```bash
export GROQ_API_KEY="gsk-..."
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

Open **http://localhost:3000** — upload `sample_data/sample_sales.csv` to try it immediately.

### Docker Compose (production-like)

```bash
cp .env.example .env
# Edit .env — set GROQ_API_KEY (get from console.groq.com)

docker compose up --build
```

Services:
- Frontend → http://localhost:3000
- API → http://localhost:8000
- API docs → http://localhost:8000/docs

---

## API Reference

All endpoints except `/health` and `/api/upload-data` require an `X-Session-Id` header
returned by `POST /api/upload-data`.

| Method | Endpoint | Rate limit | Description |
|--------|----------|------------|-------------|
| `POST` | `/api/upload-data` | 10/min | Upload CSV, get `session_id` |
| `GET` | `/api/analyze` | 30/min | Summary stats, outlier detection + data preview |
| `POST` | `/api/generate-insights` | 5/min | LLM-generated insights (cached) |
| `POST` | `/api/query` | 10/min | Natural language Q&A |
| `GET` | `/api/session/status` | — | Session liveness + TTL remaining |
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

Test coverage: **83%** across three test layers — no live API calls are made in any test.

| File | Layer | What is covered |
|---|---|---|
| `test_data_processor.py` | **Unit** | CSV loading, 50 MB hard limit, stats accuracy, correlation, trend, outlier detection |
| `test_llm_engine.py` | **Unit** | API key validation, `_build_summary_text`, `_parse_json`, tenacity retry on `NetworkError` |
| `test_api_routes.py` | **Integration** | All 6 endpoints via FastAPI `TestClient` — upload, analyze, insights (cache hit/miss), query, health, session delete |
| `test_edge_cases.py` | **Edge case** | Unicode column names, single-row CSV, all-null columns, extreme outliers, data quality score, session TTL endpoint |
| `test_session_store.py` | **Unit** | Session CRUD, TTL, cross-session isolation |
| `test_cache.py` | **Unit** | Cache hit/miss, SHA-256 keying, LRU eviction |

---

## Benchmark

AutoInsight ships a reproducible NL-to-query accuracy benchmark against
`sample_data/sample_sales.csv` — a 15-question suite covering easy aggregations
through hard multi-step and ambiguous-column cases.

```bash
# Structural contract check — no API calls, runs in < 1 s (CI-safe):
python3 scripts/benchmark.py --mock

# Full rubric evaluation (requires GROQ_API_KEY):
export GROQ_API_KEY="gsk-..."
python3 scripts/benchmark.py --live

# Filter to a specific category:
python3 scripts/benchmark.py --live --category "Multi-step"

# Save results for tracking over time:
python3 scripts/benchmark.py --live --output results/benchmark_$(date +%Y%m%d).json
```

Sample `--live` output:

```
──────────────────────────────────────────────────────────────────────
  AutoInsight NL Benchmark — LIVE mode (real Groq API calls)
──────────────────────────────────────────────────────────────────────
  Model     : llama-3.3-70b-versatile
  Dataset   : sample_sales.csv  (500 rows × 9 cols)
  Questions : 15
──────────────────────────────────────────────────────────────────────
  [01/15] What is the average sales_usd?          ✓  [0.9s]  conf=high
  [08/15] Which region has the highest avg ...    ✓  [1.2s]  conf=medium
  [11/15] What is the average satisfaction ...    ✓  [1.1s]  conf=medium
  ...

  Structural accuracy : 15/15 (100%)
  Rubric accuracy     : 13/15  (87%)

  By difficulty:
    easy      ██████████  3/3  (100%)
    medium    ████████░░  3/4   (75%)
    hard      ████████░░  7/8   (88%)
──────────────────────────────────────────────────────────────────────
```

| Category | Difficulty | What it tests |
|---|---|---|
| Single-column aggregation | Easy | Baseline: mean/median/max from stats |
| Cross-column reasoning | Medium | Correlation awareness |
| Trend detection | Medium | Rolling-window trend direction |
| Multi-step aggregation | **Hard** | Filter + group-by — classic NL failure mode |
| Ambiguous column reference | **Hard** | `"satisfaction"` → `customer_satisfaction` |
| Null-aware reasoning | **Hard** | Acknowledging missing data in the `caveat` field |
| Temporal comparison | **Hard** | First-half vs second-half delta reasoning |

---

## Hard Cases AutoInsight Handles Well

The NL-querying space is crowded. Below are three classes of query that are
non-trivial to handle correctly — and how AutoInsight approaches them.

### 1. Multi-step aggregation

**Query:** *"Which region has the highest average sales_usd?"*

A naive implementation forwards raw column names to the LLM with no context.
AutoInsight builds a structured summary (shape, numeric stats, categorical
distributions, correlations, trends) so the model has the statistical
context to reason about group-level aggregations without raw row access.

**Sample response:**
```json
{
  "answer": "Based on the dataset summary, the North region consistently shows
             the highest mean sales_usd, particularly in the earlier months
             before the overall declining trend took hold.",
  "confidence": "medium",
  "caveat": "Exact per-region averages are not in the summary; this is inferred
             from the top_values distribution and the detected trend direction."
}
```

### 2. Ambiguous column reference

**Query:** *"What is the average satisfaction score?"*

The column is named `customer_satisfaction`, not `satisfaction`. AutoInsight
shares the full sanitised column list in every system prompt, so the model
resolves the reference correctly rather than hallucinating a non-existent field.

**Sample response:**
```json
{
  "answer": "The mean customer_satisfaction score is approximately 4.3 (scale
             appears to be 1–5). It shows a declining trend of ~15% over the
             dataset period.",
  "confidence": "high",
  "caveat": "~3% of customer_satisfaction values are missing, which may
             slightly understate the true mean."
}
```

### 3. Null-aware reasoning

**Query:** *"What is the average marketing_spend, and does missing data affect the result?"*

AutoInsight's summary explicitly includes `missing_pct` per column and passes
it to the model. The LLM can then surface data quality caveats in the
structured `caveat` field instead of silently ignoring gaps.

**Sample response:**
```json
{
  "answer": "The mean marketing_spend is approximately $980 per row.
             Around 2% of rows have missing values for this column.",
  "confidence": "high",
  "caveat": "The 2% missing rate is low and unlikely to meaningfully skew
             the mean, but rows with zero spend may be excluded rather than
             truly absent — worth verifying in the raw data."
}
```

> Run `python3 scripts/benchmark.py --live` to reproduce these results
> against the live model on your own API key.

---

## Environment Variables

See `.env.example` for the full reference. Key variables:

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GROQ_API_KEY` | **Yes** | — | Your Groq API key ([get free key](https://console.groq.com)) |
| `REDIS_URL` | No | `redis://localhost:6379/0` | Redis connection (omit = memory fallback) |
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
- [x] 40 tests, 83% coverage — unit + integration + edge case (no live API calls)
- [x] `.env.example` documents every configurable variable
- [x] Reproducible NL accuracy benchmark (15-question suite, `--mock` CI-safe)
- [x] Conversation history in Ask tab with confidence badges and timestamps

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

**"What happens if the Groq API goes down?"**
`tenacity` retries up to 4 times with exponential backoff (2–30s). After that, the route returns a clean 502 with a user-friendly message — no stack trace exposed.

**"How would you scale this to 10,000 concurrent users?"**
Redis is already shared across workers, rate limiting is in place, and `docker-compose` can scale `backend` replicas with `--scale backend=4`. The next bottleneck would be LLM throughput — solved by adding a job queue (Celery + Redis) for insight generation.

**"Why not send the raw CSV to the LLM?"**
Cost, latency, and privacy. A 10k-row CSV at ~50 bytes/row is 500KB — roughly 125k tokens. The summary is ~130 words. Same insights, 1000× cheaper and faster.

**"How do you know the NL answers are accurate?"**
`scripts/benchmark.py` is a 15-question rubric suite against `sample_sales.csv` with hand-crafted ground truth. It covers easy aggregations, cross-column reasoning, multi-step group-bys (the classic LLM failure mode), ambiguous column references, null-aware answers, and temporal comparisons. Run `python3 scripts/benchmark.py --mock` in CI for a zero-cost structural contract check, or `--live` with a real key for full rubric scoring.

---

## License

MIT
