# Implementation Plan: Intelligent Observability & Event Watchdog

> Wolters Kluwer Assessment — Project 3
> Architect: Chetan Singh Chouhan | AI Engineer: Claude Code

---

## Overview

A Python-based, API-first observability service that ingests logs, detects anomalies via Z-score + Claude AI narrative, fires simulated webhooks, and visualizes health trends on a Streamlit dashboard. Built with FastAPI + PostgreSQL (Neon.tech) + uv, delivered by Wednesday evening.

---

## Architecture Decisions

- **uv over pip**: Modern, fast, lockfile-based — `pyproject.toml` is the single source of truth
- **Neon.tech over Docker**: Free serverless Postgres, zero setup, connection string in `.env`
- **asyncpg + SQLAlchemy async**: Required for FastAPI's async model; enables connection pooling story for recruiter
- **Statistical-first, Claude-second**: Z-score triggers the anomaly; Claude writes the incident narrative — separates concerns and keeps Claude calls minimal/cheap
- **Streamlit separate process**: Dashboard calls the FastAPI `/health/trends`, `/anomalies`, `/webhook/events` endpoints — clean separation, no coupling
- **Vertical slicing**: Each task delivers a working end-to-end path, not a horizontal layer

---

## Dependency Graph

```
pyproject.toml + scaffold
        │
        ├── app/config.py (.env settings)
        │         │
        │         └── app/database.py (engine + session)
        │                   │
        │                   ├── models/ (LogEntry, Anomaly, WebhookEvent)
        │                   │       │
        │                   │       └── alembic migrations
        │                   │
        │                   └── schemas/ (Pydantic — parallel to models)
        │
        ├── [SLICE 1] logs router → LogEntry model → DB
        │
        ├── [SLICE 2] anomaly_detector + claude_service → Anomaly model → DB
        │                   triggered by log ingest pipeline
        │
        ├── [SLICE 3] webhook_service + webhooks router → WebhookEvent model → DB
        │                   triggered by anomaly detection
        │
        ├── [SLICE 4] health router → trends aggregation query
        │
        ├── [SLICE 5] Streamlit dashboard → calls FastAPI endpoints
        │
        ├── [SLICE 6] scripts/generate_logs.py → calls POST /logs/ingest
        │
        ├── [SLICE 7] tests/ → all slices complete
        │
        └── [SLICE 8] README + prompts.md + GitHub repo + PR
```

---

## Phase 1: Scaffold & Foundation

### Task 1: Project Scaffold + prompts.md (Turn 1)
**Description:** Initialize the project with uv, create all directories, base config, .env.example, .gitignore, and — critically — `prompts.md` with all architect instructions logged from this conversation onward.

**Acceptance criteria:**
- [ ] `uv init` run, `pyproject.toml` exists with project metadata
- [ ] All directories exist: `app/`, `app/models/`, `app/schemas/`, `app/routers/`, `app/services/`, `app/middleware/`, `dashboard/`, `alembic/`, `tests/`, `scripts/`, `tasks/`
- [ ] `.env.example` has `DATABASE_URL`, `ANTHROPIC_API_KEY`, `WEBHOOK_URL`, `APP_ENV`
- [ ] `.gitignore` excludes `.env`, `.venv/`, `__pycache__/`, `*.pyc`, `alembic/versions/*.py` (no — keep migrations), `.coverage`
- [ ] `prompts.md` created with Turn 1 entry logging all architect instructions to date
- [ ] `app/config.py` loads settings from `.env` via `pydantic-settings`

**Verification:**
- [ ] `uv sync` runs without error
- [ ] `python -c "from app.config import settings; print(settings.app_env)"` prints value
- [ ] `prompts.md` exists and has Turn 1 entry

**Files touched:** `pyproject.toml`, `app/config.py`, `.env.example`, `.gitignore`, `prompts.md`

**Dependencies:** None — this is the foundation

**Estimated scope:** S

---

### Task 2: Database Layer — Engine, Models, Migrations
**Description:** Wire up async SQLAlchemy with asyncpg to Neon.tech. Define all three ORM models. Run Alembic migrations to create tables.

**Acceptance criteria:**
- [ ] `app/database.py` has `async_engine`, `AsyncSessionLocal`, `get_db` dependency
- [ ] `LogEntry` model: `id (UUID PK)`, `service_name`, `level (Enum)`, `message`, `timestamp`, `metadata (JSON)`
- [ ] `Anomaly` model: `id`, `service_name`, `detected_at`, `window_start`, `window_end`, `error_count`, `z_score`, `threshold_breached`, `ai_narrative`, `severity (Enum)`, `webhook_fired (bool)`
- [ ] `WebhookEvent` model: `id`, `anomaly_id (FK → Anomaly)`, `fired_at`, `payload (JSON)`, `response_status`
- [ ] Alembic configured to use `DATABASE_URL` from settings
- [ ] `alembic upgrade head` creates all three tables in Neon

**Verification:**
- [ ] `alembic upgrade head` runs without error
- [ ] Connect to Neon and confirm tables exist: `\dt` shows `log_entries`, `anomalies`, `webhook_events`

**Files touched:** `app/database.py`, `app/models/log_entry.py`, `app/models/anomaly.py`, `app/models/webhook_event.py`, `app/models/__init__.py`, `alembic.ini`, `alembic/env.py`, `alembic/versions/<timestamp>_init.py`

**Dependencies:** Task 1

**Estimated scope:** M

---

## Checkpoint: Foundation
- [ ] `uv sync` clean
- [ ] `alembic upgrade head` clean — tables exist in Neon
- [ ] Config loads from `.env`
- [ ] prompts.md has Turn 1 entry

---

## Phase 2: Vertical Slice 1 — Log Ingestion

### Task 3: Pydantic Schemas + FastAPI App Bootstrap
**Description:** Define all Pydantic request/response schemas. Bootstrap the FastAPI app with CORS, lifespan, and router registration. Add rate limiting via slowapi.

**Acceptance criteria:**
- [ ] `app/schemas/log_entry.py`: `LogEntryCreate` (request), `LogEntryResponse` (response), `LogEntryBatch`
- [ ] `app/schemas/anomaly.py`: `AnomalyResponse`
- [ ] `app/schemas/webhook_event.py`: `WebhookEventResponse`
- [ ] `app/main.py`: FastAPI app with title, version, lifespan (DB startup check), CORS middleware, slowapi `RateLimiter`
- [ ] `GET /health` returns `{"status": "ok", "version": "0.1.0"}`
- [ ] OpenAPI docs available at `http://localhost:8000/docs`

**Verification:**
- [ ] `uvicorn app.main:app --reload` starts without error
- [ ] `curl http://localhost:8000/health` returns `{"status": "ok"}`
- [ ] `http://localhost:8000/docs` loads OpenAPI UI

**Files touched:** `app/main.py`, `app/schemas/log_entry.py`, `app/schemas/anomaly.py`, `app/schemas/webhook_event.py`, `app/schemas/__init__.py`, `app/routers/health.py`

**Dependencies:** Task 2

**Estimated scope:** M

---

### Task 4: Log Ingestion Router (POST /logs/ingest + GET /logs)
**Description:** Implement the log ingestion endpoint with rate limiting (10 req/min per IP on ingest), batch support (up to 100 logs), and query endpoint with filters.

**Acceptance criteria:**
- [ ] `POST /logs/ingest` accepts single `LogEntryCreate` or `LogEntryBatch` (list)
- [ ] Rate limited: 10 requests/minute per IP (slowapi)
- [ ] Returns `201` with list of created `LogEntryResponse`
- [ ] `GET /logs` supports query params: `service_name`, `level`, `from_ts`, `to_ts`, `limit` (default 100)
- [ ] `GET /logs/{id}` returns single log or `404`
- [ ] Logs written to `log_entries` table in Neon

**Verification:**
- [ ] `curl -X POST http://localhost:8000/logs/ingest -H "Content-Type: application/json" -d '{"service_name":"api","level":"ERROR","message":"test error","timestamp":"2026-05-26T10:00:00Z"}'` returns 201
- [ ] `curl http://localhost:8000/logs` returns the ingested log
- [ ] Exceeding 10 req/min returns `429 Too Many Requests`

**Files touched:** `app/routers/logs.py`, `app/middleware/rate_limiter.py`

**Dependencies:** Task 3

**Estimated scope:** M

---

## Checkpoint: Slice 1 — Log Ingestion Working
- [ ] Can POST a log and GET it back
- [ ] Rate limiting returns 429 after 10 req/min
- [ ] Neon DB has rows in `log_entries`

---

## Phase 3: Vertical Slice 2 — Anomaly Detection Pipeline

### Task 5: Anomaly Detector Service (Z-score)
**Description:** Implement statistical anomaly detection. After each log ingest, run detection on the last 5-minute window for that service. Z-score > 2.0 = anomaly.

**Acceptance criteria:**
- [ ] `app/services/anomaly_detector.py` has `detect(service_name, db)` async function
- [ ] Queries `log_entries` for ERROR/CRITICAL in last 5-min window
- [ ] Computes Z-score against historical 1-hour baseline (rolling)
- [ ] If Z-score > 2.0: creates `Anomaly` record in DB, sets `severity` based on Z-score band:
  - 2.0–3.0 → LOW, 3.0–4.0 → MEDIUM, 4.0–5.0 → HIGH, >5.0 → CRITICAL
- [ ] Returns `Anomaly` object or `None`
- [ ] Called automatically from `POST /logs/ingest` (background task)

**Verification:**
- [ ] Unit test: inject mock error counts, assert Z-score computed correctly
- [ ] Integration: POST 20 ERROR logs in rapid succession → `GET /anomalies` returns 1 anomaly

**Files touched:** `app/services/anomaly_detector.py`, `app/routers/logs.py` (add background task call)

**Dependencies:** Task 4

**Estimated scope:** M

---

### Task 6: Claude Service — AI Incident Narrative
**Description:** When an anomaly is detected, call Claude API to generate a 3-sentence incident narrative and update the Anomaly record.

**Acceptance criteria:**
- [ ] `app/services/claude_service.py` has `generate_narrative(anomaly, recent_logs)` async function
- [ ] Uses `claude-sonnet-4-6` model via Anthropic SDK
- [ ] Prompt: "You are an SRE. Given these log entries from [service_name] in the last 5 minutes: [...]. Summarize the incident, likely cause, and recommended action in 3 sentences."
- [ ] Response stored in `Anomaly.ai_narrative` in DB
- [ ] Graceful fallback: if Claude call fails, narrative = "AI narrative unavailable — manual review required"
- [ ] `GET /anomalies` returns anomalies with `ai_narrative` populated

**Verification:**
- [ ] `GET /anomalies/{id}` shows non-empty `ai_narrative`
- [ ] Unit test: mock Anthropic client, assert narrative stored correctly
- [ ] Unit test: simulate API failure, assert fallback message stored

**Files touched:** `app/services/claude_service.py`, `app/services/anomaly_detector.py` (call claude after detection), `app/routers/anomalies.py`

**Dependencies:** Task 5

**Estimated scope:** M

---

## Checkpoint: Slice 2 — Anomaly Pipeline Working
- [ ] POST errors → anomaly auto-detected → Claude narrative generated
- [ ] `GET /anomalies` returns anomalies with AI narratives
- [ ] Anomalies in Neon `anomalies` table

---

## Phase 4: Vertical Slice 3 — Webhook Pipeline

### Task 7: Webhook Service + Router
**Description:** When an anomaly is detected, fire a simulated webhook to `POST /webhook/receive`. Log the event. Expose GET endpoint to list all fired events.

**Acceptance criteria:**
- [ ] `app/services/webhook_service.py` has `fire(anomaly, db)` async function
- [ ] Uses `httpx.AsyncClient` to POST to `WEBHOOK_URL` (defaults to `http://localhost:8000/webhook/receive`)
- [ ] Creates `WebhookEvent` record with payload, fired_at, response_status
- [ ] Updates `Anomaly.webhook_fired = True`
- [ ] `POST /webhook/receive` accepts any JSON payload, logs it, returns `{"received": true}`
- [ ] `GET /webhook/events` returns last 50 webhook events
- [ ] Called from anomaly detection pipeline after `Anomaly` is created

**Verification:**
- [ ] POST errors → anomaly detected → `GET /webhook/events` shows 1 event with status 200
- [ ] `GET /anomalies/{id}` shows `webhook_fired: true`

**Files touched:** `app/services/webhook_service.py`, `app/routers/webhooks.py`, `app/services/anomaly_detector.py` (add webhook fire call)

**Dependencies:** Task 6

**Estimated scope:** M

---

## Checkpoint: Slice 3 — Full Pipeline Working
- [ ] Ingest logs → anomaly detected → Claude narrative → webhook fired → all 3 tables have data
- [ ] `GET /webhook/events` shows fired events

---

## Phase 5: Vertical Slice 4 — Health Trends

### Task 8: Health Trends Endpoint
**Description:** Aggregate error counts into 5-minute buckets for the dashboard. Power the `GET /health/trends` endpoint.

**Acceptance criteria:**
- [ ] `GET /health/trends` accepts optional `service_name`, `hours` (default 6) query params
- [ ] Returns time-series: list of `{bucket: datetime, error_count: int, warn_count: int, info_count: int, service_name: str}`
- [ ] Query uses `date_trunc('minute', timestamp)` bucketed to 5-min intervals
- [ ] `GET /health` returns `{"status": "ok", "db": "connected", "version": "0.1.0"}`

**Verification:**
- [ ] `curl "http://localhost:8000/health/trends?hours=1"` returns non-empty list after log ingestion

**Files touched:** `app/routers/health.py`

**Dependencies:** Task 4

**Estimated scope:** S

---

## Phase 6: Vertical Slice 5 — Streamlit Dashboard

### Task 9: Streamlit Dashboard (5 Charts)
**Description:** Build the live dashboard that polls the FastAPI endpoints every 10 seconds and renders 5 charts.

**Acceptance criteria:**
- [ ] `dashboard/app.py` connects to `http://localhost:8000`
- [ ] **Chart 1**: Error Rate Over Time — line chart from `/health/trends`, 5-min buckets
- [ ] **Chart 2**: Anomaly Events Timeline — bar/scatter from `/anomalies`, color by severity
- [ ] **Chart 3**: Service Health Matrix — table with current error rate + status badge per service
- [ ] **Chart 4**: Webhook Fired Log — table of last 10 events from `/webhook/events`
- [ ] **Chart 5**: AI Narrative Panel — text display of latest anomaly's `ai_narrative`
- [ ] Auto-refreshes every 10 seconds via `st.rerun()` with `time.sleep(10)`
- [ ] Page title: "Observability Watchdog — Live Dashboard"

**Verification:**
- [ ] `streamlit run dashboard/app.py` starts without error
- [ ] All 5 sections render with data after running log generator
- [ ] Auto-refresh visible (timestamp updates every ~10s)

**Files touched:** `dashboard/app.py`

**Dependencies:** Tasks 7, 8 (all API endpoints must exist)

**Estimated scope:** M

---

## Phase 7: Synthetic Log Generator

### Task 10: Log Generator Script
**Description:** Build a script that generates realistic synthetic logs including deliberate error spikes to demo anomaly detection.

**Acceptance criteria:**
- [ ] `scripts/generate_logs.py` sends logs to `POST /logs/ingest`
- [ ] Generates 3 services: `api-gateway`, `auth-service`, `payment-service`
- [ ] Baseline: mix of INFO/WARN at ~1 log/sec for 5 minutes
- [ ] Spike: 30 ERROR logs in 60 seconds for `payment-service` (triggers anomaly)
- [ ] Uses `Faker` for realistic message content
- [ ] Prints progress and reports anomaly count at end
- [ ] Configurable via CLI args: `--services`, `--spike`, `--duration`

**Verification:**
- [ ] `python scripts/generate_logs.py` runs without error
- [ ] `GET /anomalies` shows at least 1 anomaly after script completes
- [ ] Dashboard shows spike in error rate chart

**Files touched:** `scripts/generate_logs.py`

**Dependencies:** Task 4 (logs API must exist)

**Estimated scope:** S

---

## Checkpoint: Full MVP Working
- [ ] Run `python scripts/generate_logs.py` end-to-end
- [ ] `GET /anomalies` returns anomalies with Claude narratives
- [ ] `GET /webhook/events` shows fired webhooks
- [ ] Streamlit dashboard shows all 5 charts with real data
- [ ] All 3 Neon tables populated

---

## Phase 8: Tests

### Task 11: Test Suite (≥ 80% coverage)
**Description:** Write unit and integration tests covering the anomaly detector, log ingestion, and webhook pipeline.

**Acceptance criteria:**
- [ ] `tests/conftest.py`: async test client (httpx), in-memory SQLite test DB fixture
- [ ] `tests/test_logs.py`: test POST /logs/ingest (single, batch, invalid input, rate limit)
- [ ] `tests/test_anomaly_detector.py`: unit test Z-score logic, mock DB, assert anomaly created at Z > 2.0
- [ ] `tests/test_webhooks.py`: test POST /webhook/receive, GET /webhook/events
- [ ] Claude calls mocked via `pytest-mock` — no real API calls in tests
- [ ] `pytest tests/ --cov=app --cov-report=term-missing` reports ≥ 80%

**Verification:**
- [ ] `pytest tests/ -v` — all tests green
- [ ] Coverage report shows ≥ 80% on `app/`

**Files touched:** `tests/conftest.py`, `tests/test_logs.py`, `tests/test_anomaly_detector.py`, `tests/test_webhooks.py`

**Dependencies:** Tasks 7, 8 (all routes exist)

**Estimated scope:** L

---

## Phase 9: Documentation + GitHub

### Task 12: README + Architecture + prompts.md final
**Description:** Write the README with setup instructions, architecture diagram (ASCII), and ensure prompts.md has all turns logged.

**Acceptance criteria:**
- [ ] `README.md`: project title, what it does, quick start (5 commands), API reference table, architecture ASCII diagram, tech stack table, "Next Steps" (auth, Docker, cloud deploy)
- [ ] `prompts.md`: all architect instructions from Turn 1 to final turn logged with timestamps
- [ ] `SPEC.md` up to date (already is)

**Files touched:** `README.md`, `prompts.md`

**Dependencies:** All tasks complete

**Estimated scope:** S

---

### Task 13: Git Init + Private GitHub Repo + Branch Protection + PR
**Description:** Initialize git locally, create PRIVATE GitHub repo via GitHub MCP, set branch protection on main (no direct push, PR + approval required — same as signfast project), push scaffold, raise first PR.

**Acceptance criteria:**
- [ ] `git init` in project root
- [ ] `.gitignore` excludes `.env`, `.venv/`
- [ ] Initial commit on `main` with scaffold only (no `.env`)
- [ ] GitHub repo created as **PRIVATE** via `mcp__github__create_repository`
- [ ] Branch protection on `main`: require PR, require 1 approving review, no direct push
- [ ] Feature branch `feat/task-1-scaffold` pushed
- [ ] PR raised via `create-pr` skill with labels
- [ ] **Architect approval required before every push to GitHub**

**Verification:**
- [ ] Direct push to `main` is rejected
- [ ] PR is open and shows all scaffold files, prompts.md, SPEC.md, tasks/

**Files touched:** `.gitignore`, all project files staged

**Dependencies:** Task 12

**Estimated scope:** S

> NOTE: GitHub push requires explicit architect approval each time. Never push without confirmation.

---

## Risks and Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Neon cold start latency on free tier | Medium | Use `pool_pre_ping=True` in SQLAlchemy engine |
| Claude API rate limits during testing | Medium | Mock in tests; use `generate_logs.py` sparingly |
| asyncpg + Neon SSL connection issues | High | Set `?sslmode=require` in `DATABASE_URL` |
| Streamlit auto-refresh causes flickering | Low | Use `st.empty()` containers to update in-place |
| Z-score insufficient data (cold start) | Medium | Minimum 10 historical data points required; else skip detection |

---

## Total Estimated Timeline

| Phase | Tasks | Est. Time |
|---|---|---|
| Foundation | 1–2 | 45 min |
| Log Ingestion | 3–4 | 45 min |
| Anomaly Pipeline | 5–6 | 60 min |
| Webhook Pipeline | 7 | 30 min |
| Health + Dashboard | 8–9 | 60 min |
| Log Generator | 10 | 20 min |
| Tests | 11 | 60 min |
| Docs + GitHub | 12–13 | 30 min |
| **Total** | **13 tasks** | **~6 hours** |

---

## Phase 10: Dashboard Redesign

### Task 14 (M): Minimal Dashboard Rewrite

**Description:** Replace the current 261-line multi-section dashboard with a ruthlessly minimal single-page layout based on `tasks/minimal/handoff.md`. The page answers one question: "is anything wrong right now?" Five elements visible by default — header, status hero, one sparkline, recent anomaly timeline, footer. No tabs, no KPI cards, no service health column.

**Acceptance criteria:**
- [ ] Dashboard loads at http://localhost:8501 without errors
- [ ] Status hero shows green "All systems normal" when no active anomalies
- [ ] Status hero shows "Active incident · `<service>` · **N×** above normal + first AI sentence + Investigate CTA" when anomaly exists
- [ ] Single 6h error-rate sparkline rendered via Altair (height ~110px) with red dots at anomaly buckets
- [ ] Recent timeline: one `st.expander` row per anomaly — collapsed shows `HH:MM · service · N× normal`; expanded shows full AI narrative, error count vs baseline, webhook status
- [ ] Sidebar contains exactly 2 controls: metric style selectbox (× baseline / 0–100 score / Plain English / Z-score) and chart toggle
- [ ] Auto-refresh every 10s via `streamlit-autorefresh` package (not JS reload)
- [ ] Dark theme applied via `.streamlit/config.toml`
- [ ] `metric_readings()` helper added to `app/services/anomaly_detector.py`
- [ ] `AnomalyResponse` extended with `baseline_mean: float | None`, `top_errors: list[dict]`, `trend_direction: str | None`
- [ ] All existing `uv run pytest tests/ -v` tests still pass

**Verification:**
- [ ] `uv run pytest tests/ -v --cov=app` — all green, coverage ≥ 80%
- [ ] Playwright MCP: navigate to http://localhost:8501, screenshot hero, verify expander opens/closes
- [ ] Run `generate_logs.py` spike, confirm hero flips to "Active incident"

**Dependencies:** Tasks 1–13 complete ✅

**Files touched:**
- `app/services/anomaly_detector.py` — add `metric_readings()` helper
- `app/schemas/anomaly.py` — extend `AnomalyResponse` with `baseline_mean`, `top_errors`, `trend_direction`
- `app/services/anomaly_service.py` — populate new schema fields on save/return
- `dashboard/app.py` — full rewrite (~60 lines)
- `dashboard/cards.py` — new file: `header_html()` + `hero_html()` f-string templates
- `.streamlit/config.toml` — new file: dark theme
- `pyproject.toml` — add `streamlit-autorefresh` dependency

**Implementation slices (incremental order):**
1. `metric_readings()` in anomaly_detector — pure function, test first
2. Schema + serializer fields — no dashboard changes yet
3. `.streamlit/config.toml` + `pyproject.toml` dep
4. `dashboard/cards.py` templates
5. `dashboard/app.py` rewrite
6. Playwright smoke test

**Estimated scope:** Medium (6–7 files, ~2h)
