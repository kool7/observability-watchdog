# Observability Watchdog

> Intelligent log anomaly detection with AI-powered incident narratives, webhook alerts, and a live dashboard.

[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-green.svg)](https://fastapi.tiangolo.com)
[![uv](https://img.shields.io/badge/uv-package%20manager-purple.svg)](https://docs.astral.sh/uv)
[![Tests](https://img.shields.io/badge/tests-110%20passed-brightgreen.svg)](#running-tests)
[![Coverage](https://img.shields.io/badge/coverage-88%25-brightgreen.svg)](#running-tests)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

An API-first observability service that ingests application logs, detects error spikes using statistical analysis and Claude AI, fires simulated webhook alerts when thresholds are breached, and visualizes health trends in real time. Built with FastAPI and PostgreSQL on a fully async stack.

---

## Architecture

```
  ┌─────────────────────────────────────────────────────────────────────┐
  │                     Observability Watchdog                          │
  │                                                                     │
  │   POST /logs/ingest                                                 │
  │  ─────────────────▶  Log Router  ──▶  log_service  ──▶  PostgreSQL  │
  │  (single or batch)        │            (persist)        (Neon.tech)  │
  │                           │                                  ▲      │
  │                           ▼                                  │      │
  │                   anomaly_service                            │      │
  │                  (Z-score on 5-min                           │      │
  │                   rolling window)                            │      │
  │                           │                                  │      │
  │               ┌───────────┴───────────┐                      │      │
  │               ▼                       ▼                      │      │
  │       claude_service          webhook_service  ──────────────┘      │
  │   (AI incident narrative)   (fire + log alert)                      │
  │    claude-sonnet-4-6          POST /webhook/receive                 │
  │               │                                                     │
  └───────────────┼─────────────────────────────────────────────────────┘
                  │
                  ▼
        GET /health/trends          GET /anomalies        GET /logs
               │                         │                    │
               └─────────────────────────┴────────────────────┘
                                         │
                                         ▼
                               Streamlit Dashboard
                          (5 charts · auto-refresh 10s)
```

---

## Features

- **Log Ingestion API** — Ingest single or batch log entries via REST with per-IP rate limiting (10 req/min on `POST /logs/ingest`)
- **Statistical Anomaly Detection** — Z-score analysis on 5-minute rolling windows; severity bands from LOW to CRITICAL
- **Claude AI Incident Narratives** — Every detected anomaly gets a 3-sentence SRE-style root cause summary from Claude
- **Simulated Webhook Alerts** — Fires and logs webhook events when anomaly thresholds are breached
- **Live Streamlit Dashboard** — 5 charts including error rate timeline, anomaly events, service health matrix, and AI narratives; auto-refreshes every 10 seconds
- **Production-Grade Async Stack** — FastAPI + asyncpg + SQLAlchemy async with connection pooling on serverless Postgres (Neon.tech)

---

## Tech Stack

| Layer           | Technology                                       |
| --------------- | ------------------------------------------------ |
| API Framework   | FastAPI + uvicorn                                |
| Database        | PostgreSQL via Neon.tech (serverless, free tier) |
| ORM / Pool      | SQLAlchemy async + asyncpg                       |
| Migrations      | Alembic                                          |
| AI / LLM        | Anthropic Claude API (claude-sonnet-4-6)         |
| Dashboard       | Streamlit                                        |
| Rate Limiting   | slowapi                                          |
| Package Manager | uv (pyproject.toml)                              |
| Testing         | pytest + pytest-asyncio + httpx                  |
| Linting         | ruff + black + mypy                              |

---

## Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/getting-started/installation/) installed
- A [Neon.tech](https://neon.tech) free account (PostgreSQL connection string)
- An [Anthropic API key](https://console.anthropic.com)

---

## Quick Start

```bash
# 1. Clone and install dependencies
git clone https://github.com/kool7/observability-watchdog.git
cd observability-watchdog
uv sync

# 2. Configure environment
cp .env.example .env
# Edit .env — set DATABASE_URL and ANTHROPIC_API_KEY

# 3. Run database migrations (DATABASE_URL must point to an existing Neon database)
uv run alembic upgrade head

# 4. Start the API server
uv run uvicorn app.main:app --reload --port 8000

# 5. Start the dashboard (new terminal)
uv run streamlit run dashboard/app.py
```

Open **http://localhost:8000/docs** for the interactive API explorer.
Open **http://localhost:8501** for the live dashboard.

---

## Generating Demo Data

Seed the system with synthetic logs including a deliberate error spike to trigger anomaly detection:

```bash
uv run python scripts/generate_logs.py
```

This simulates 3 services (`api-gateway`, `auth-service`, `payment-service`) and injects a spike on `payment-service` to demonstrate the full detection → narrative → webhook pipeline.

---

## API Reference

### Logs

| Method | Endpoint       | Description                                       |
| ------ | -------------- | ------------------------------------------------- |
| `POST` | `/logs/ingest` | Ingest one or a batch of log entries              |
| `GET`  | `/logs`        | Query logs — filter by service, level, time range |
| `GET`  | `/logs/{id}`   | Retrieve a single log entry                       |

### Anomalies

| Method | Endpoint          | Description                                    |
| ------ | ----------------- | ---------------------------------------------- |
| `GET`  | `/anomalies`      | List all detected anomalies with AI narratives |
| `GET`  | `/anomalies/{id}` | Retrieve a single anomaly detail               |

### Health

| Method | Endpoint         | Description                                |
| ------ | ---------------- | ------------------------------------------ |
| `GET`  | `/health`        | Liveness check                             |
| `GET`  | `/health/trends` | Error rates aggregated in 5-minute buckets |

### Webhooks

| Method | Endpoint           | Description                                           |
| ------ | ------------------ | ----------------------------------------------------- |
| `POST` | `/webhook/receive` | Simulated webhook sink — accepts and logs any payload |
| `GET`  | `/webhook/events`  | List all fired webhook events                         |

---

## Environment Variables

Copy `.env.example` to `.env` and fill in your values:

```env
DATABASE_URL=postgresql+asyncpg://user:password@ep-xxxx.neon.tech/watchdog?sslmode=require
ANTHROPIC_API_KEY=sk-ant-...
WEBHOOK_URL=http://localhost:8000/webhook/receive
APP_ENV=development
CLAUDE_MODEL=claude-sonnet-4-6
CLAUDE_MAX_TOKENS=256
```

---

## Running Tests

110 tests, 88% coverage across all service, router, and middleware layers:

```bash
uv run pytest tests/ -v --cov=app --cov-report=term-missing
```

Run the full lint suite:

```bash
uv run ruff check . && uv run black --check . && uv run mypy app/
```

---

## Known Gaps & Roadmap

Auth was intentionally deferred to keep the MVP scope focused on the detection pipeline; production hardening would address these first:

- **Authentication** — Add JWT/OAuth2 bearer token auth on all write endpoints (priority for regulated-industry deployment)
- **Docker Compose** — Containerize the API and dashboard for one-command local setup
- **Cloud Deployment** — Deploy to Azure App Service or AWS ECS with managed Postgres
- **Real Webhook Targets** — Integrate with Slack, PagerDuty, or Microsoft Teams
- **OpenTelemetry** — Add distributed tracing via OpenTelemetry SDK
- **Test Coverage** — Increase from 88% to ≥95% by adding integration tests for service-layer edge cases

---

## License

MIT
