# Spec: Intelligent Observability & Event Watchdog

> Wolters Kluwer Assessment — Project 3 | Vibe Coding Exercise
> Architect: Chetan Singh Chouhan | AI Engineer: Claude Code

---

## Objective

Build a Python-based, API-first observability service that:
- Ingests application/platform logs via REST API
- Detects anomalies and error spikes using statistical logic + Claude AI narrative
- Triggers simulated webhook alerts when thresholds are breached
- Visualizes health trends on a Streamlit dashboard

**Target Users:** Platform/SRE engineers monitoring application health in real time.

**Success looks like:** An engineer ingests logs, sees error spikes detected automatically, receives webhook alerts, and views a live dashboard — all through documented API calls.

---

## Tech Stack

| Layer | Technology | Rationale |
|---|---|---|
| API Framework | FastAPI | JD requirement, async-native, OpenAPI auto-docs |
| Database | PostgreSQL | Connection pooling (asyncpg), resiliency, scale — recruiter-aligned |
| ORM / Pool | SQLAlchemy async + asyncpg | Production-grade async pool with FastAPI |
| Migrations | Alembic | Schema versioning |
| Package Manager | uv | Fast, modern — pyproject.toml, no requirements.txt |
| Postgres Host | Neon.tech (free tier) | Serverless Postgres, no Docker needed, connection string via .env |
| AI / LLM | Anthropic Claude API (claude-sonnet-4-6) | Anomaly narrative + incident summary |
| Anomaly Detection | Statistical (Z-score / rolling avg) + Claude | Statistical triggers alert, Claude narrates incident |
| Dashboard | Streamlit | Fast Python-native charts, separate process |
| Rate Limiting | slowapi (Starlette middleware) | Per-IP rate limiting on ingest endpoint |
| Testing | pytest + pytest-asyncio + httpx | Async API testing |
| Linting | ruff + black + mypy | JD requirement |
| Log Generation | Faker + custom generator | Synthetic log data for demo |
| Audit Log | prompts.md | All architect instructions logged per turn |

---

## Commands

```bash
# Setup (uv)
uv init observability-watchdog  # creates pyproject.toml
uv venv && source .venv/bin/activate
uv sync                          # installs all dependencies

# Database (Neon.tech — set DATABASE_URL in .env)
alembic upgrade head

# Development
uvicorn app.main:app --reload --port 8000

# Dashboard (separate terminal)
streamlit run dashboard/app.py

# Generate synthetic logs
python scripts/generate_logs.py

# Tests
pytest tests/ -v --cov=app --cov-report=term-missing

# Lint
ruff check . && black --check . && mypy app/
```

---

## Project Structure

```
observability-watchdog/
├── app/
│   ├── main.py              # FastAPI app entry, middleware, routers
│   ├── config.py            # Settings via pydantic-settings
│   ├── database.py          # Async SQLAlchemy engine + session factory
│   ├── models/
│   │   ├── log_entry.py     # LogEntry ORM model
│   │   ├── anomaly.py       # Anomaly ORM model
│   │   └── webhook_event.py # WebhookEvent ORM model
│   ├── schemas/
│   │   ├── log_entry.py     # Pydantic request/response schemas
│   │   ├── anomaly.py
│   │   └── webhook_event.py
│   ├── routers/
│   │   ├── logs.py          # POST /logs/ingest, GET /logs
│   │   ├── anomalies.py     # GET /anomalies
│   │   ├── health.py        # GET /health, GET /health/trends
│   │   └── webhooks.py      # POST /webhook/receive (simulated sink)
│   ├── services/
│   │   ├── anomaly_detector.py  # Statistical detection (Z-score)
│   │   ├── claude_service.py    # Claude API — incident narrative
│   │   └── webhook_service.py   # Fires webhook on threshold breach
│   └── middleware/
│       └── rate_limiter.py  # slowapi rate limiting
├── dashboard/
│   └── app.py               # Streamlit dashboard
├── alembic/
│   └── versions/            # Migration files
├── tests/
│   ├── conftest.py
│   ├── test_logs.py
│   ├── test_anomaly_detector.py
│   └── test_webhooks.py
├── scripts/
│   └── generate_logs.py     # Synthetic log + spike generator
├── prompts.md               # Audit log of all architect instructions
├── SPEC.md                  # This file
├── pyproject.toml           # uv-managed dependencies
├── alembic.ini
├── .env.example
├── .gitignore
└── README.md
```

---

## API Endpoints (Contract-First)

### Logs
| Method | Path | Description |
|---|---|---|
| `POST` | `/logs/ingest` | Ingest one or batch of log entries |
| `GET` | `/logs` | Query logs with filters (level, service, time range) |
| `GET` | `/logs/{id}` | Get single log entry |

### Anomalies
| Method | Path | Description |
|---|---|---|
| `GET` | `/anomalies` | List detected anomalies with AI narrative |
| `GET` | `/anomalies/{id}` | Single anomaly detail |

### Health
| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Service liveness check |
| `GET` | `/health/trends` | Aggregated error rates by time bucket (for dashboard) |

### Webhooks
| Method | Path | Description |
|---|---|---|
| `POST` | `/webhook/receive` | Simulated webhook sink — logs payload, returns 200 |
| `GET` | `/webhook/events` | List all fired webhook events |

---

## Data Models

### LogEntry
```python
id: UUID
service_name: str
level: Enum[INFO, WARN, ERROR, CRITICAL]
message: str
timestamp: datetime
metadata: JSON  # optional key-value pairs
```

### Anomaly
```python
id: UUID
service_name: str
detected_at: datetime
window_start: datetime
window_end: datetime
error_count: int
z_score: float
threshold_breached: float
ai_narrative: str        # Claude-generated incident summary
severity: Enum[LOW, MEDIUM, HIGH, CRITICAL]
webhook_fired: bool
```

### WebhookEvent
```python
id: UUID
anomaly_id: UUID (FK)
fired_at: datetime
payload: JSON
response_status: int
```

---

## Anomaly Detection Logic

1. **Statistical Layer** — Rolling 5-minute windows, compute Z-score of error count vs historical baseline. Threshold: Z-score > 2.0 = anomaly.
2. **Claude Layer** — On anomaly detection, call Claude API with window context: "You are an SRE. Given these log entries: [...]. Summarize the incident, likely cause, and recommended action in 3 sentences."
3. **Webhook Trigger** — POST anomaly payload to `/webhook/receive` asynchronously after detection.

---

## Dashboard (Streamlit)

Charts:
- **Error Rate Over Time** — line chart, 5-min buckets, color-coded by severity
- **Anomaly Events** — timeline of detected spikes with severity badges
- **Service Health Matrix** — table of services with current error rate + status
- **Webhook Fired Log** — recent webhook events with payloads
- **AI Narrative Panel** — latest Claude-generated incident summary

Auto-refreshes every 10 seconds via `st.rerun()`.

---

## Code Style

```python
# Services return typed results, never raise HTTP exceptions
# Routers handle HTTP concerns, services handle business logic

async def detect_anomalies(
    service_name: str,
    window_minutes: int = 5,
    db: AsyncSession = Depends(get_db),
) -> list[AnomalySchema]:
    return await anomaly_detector.run(service_name, window_minutes, db)
```

- Snake_case everywhere, PascalCase for classes
- Pydantic schemas for all request/response boundaries
- Async all the way down (no sync DB calls)
- `.env` for all secrets, never hardcoded

---

## Testing Strategy

- **Framework**: pytest + pytest-asyncio + httpx AsyncClient
- **Coverage target**: ≥ 80% on `app/` directory
- **Unit tests**: `anomaly_detector.py`, `claude_service.py` (mocked Claude calls)
- **Integration tests**: Full API round-trip via httpx against test DB
- **Test DB**: Separate Neon branch or SQLite in-memory for CI speed

---

## Boundaries

- **Always:** Async DB calls, Pydantic validation on all inputs, rate limiting on ingest, update prompts.md after every build turn
- **Ask first:** Adding new dependencies, changing DB schema after migrations exist, changing Claude model version
- **Never:** Hardcode API keys or DB passwords, skip migrations for schema changes, manually edit code (Vibe Coding rules)

---

## MVP Scope (by Wednesday evening)

### In Scope
- [x] Log ingestion API with rate limiting
- [x] Statistical anomaly detection (Z-score)
- [x] Claude AI incident narrative on anomaly
- [x] Webhook simulation (fire + receive + log)
- [x] Streamlit dashboard (5 charts)
- [x] Synthetic log generator script
- [x] PostgreSQL with async connection pool
- [x] pytest suite ≥ 80% coverage
- [x] prompts.md audit log
- [x] README + architecture diagram (text)

### Out of Scope
- Real cloud deployment
- Authentication/JWT (mention in README as next step)
- Multi-tenant support
- Real Slack/PagerDuty webhook integration
- Kubernetes/Docker Compose (mention as next step)

---

## Open Questions

None — all resolved. Ready for Phase 2: Plan.
