# CLAUDE.md — Observability Watchdog

prefix: OW

## Project
Python-based, API-first Intelligent Observability & Event Watchdog.
Wolters Kluwer Assessment — Vibe Coding Exercise.

## Stack
- FastAPI + PostgreSQL (Neon.tech) + asyncpg + SQLAlchemy async + Alembic
- Claude API (claude-sonnet-4-6) for anomaly narratives
- Streamlit dashboard
- uv package manager (pyproject.toml)

## Commands
```bash
uv sync --dev
uvicorn app.main:app --reload --port 8000
streamlit run dashboard/app.py
uv run pytest tests/ -v --cov=app --cov-report=term-missing
uv run ruff check . && uv run black --check . && uv run mypy app/
alembic upgrade head
python scripts/generate_logs.py
```

## Rules
- No manual code edits (Vibe Coding)
- prompts.md updated verbatim after every architect turn
- No merge to main without PR approval (branch protection)
- Never commit .env
- Async all the way down — no sync DB calls
