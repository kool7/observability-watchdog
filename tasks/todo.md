# Task List: Observability Watchdog MVP

> Updated after every build turn | Deadline: Wednesday evening

## Phase 1: Foundation
- [ ] Task 1 (S): Project scaffold + uv init + prompts.md Turn 1
- [ ] Task 2 (M): Database layer — engine, models, Alembic migrations → Neon

## Checkpoint 1: `uv sync` clean + `alembic upgrade head` clean

## Phase 2: Log Ingestion
- [ ] Task 3 (M): Pydantic schemas + FastAPI app bootstrap + GET /health
- [ ] Task 4 (M): Log ingestion router — POST /logs/ingest + GET /logs + rate limiting

## Checkpoint 2: Can POST a log and GET it back, 429 on rate limit exceeded

## Phase 3: Anomaly Detection
- [ ] Task 5 (M): Anomaly detector service — Z-score statistical detection
- [ ] Task 6 (M): Claude service — AI incident narrative on anomaly

## Checkpoint 3: POST errors → anomaly detected → Claude narrative generated

## Phase 4: Webhook Pipeline
- [ ] Task 7 (M): Webhook service + router — fire + receive + log

## Checkpoint 4: Full pipeline — ingest → detect → narrate → webhook fired

## Phase 5: Health Trends
- [ ] Task 8 (S): Health trends endpoint — GET /health/trends (5-min buckets)

## Phase 6: Dashboard
- [ ] Task 9 (M): Streamlit dashboard — 5 charts, 10s auto-refresh

## Checkpoint 5: Full MVP working — run generate_logs.py, dashboard shows all data

## Phase 7: Log Generator
- [ ] Task 10 (S): Synthetic log generator script with spike simulation

## Phase 8: Tests
- [ ] Task 11 (L): Test suite — pytest, ≥ 80% coverage, mocked Claude

## Phase 9: Docs + GitHub
- [ ] Task 12 (S): README + ASCII architecture + prompts.md final
- [ ] Task 13 (S): git init + PRIVATE GitHub repo via MCP + branch protection (no merge without approval) + PR via create-pr skill

## Final Checkpoint: All green, PR open, repo private, branch protection active

## Standing Rules
- PRIVATE repo only
- No push to GitHub without architect approval
- No merge to main without PR + approval (branch protection)
- prompts.md updated after every turn
