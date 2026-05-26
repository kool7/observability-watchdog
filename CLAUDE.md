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

## Workflow (must follow every task, no exceptions)
- tasks/todo.md updated at START and END of every task
- Run code-reviewer agent before every PR — never skip
- After ANY code change from review comments: re-run tests AND run code-reviewer again
- Run /code-simplify after every PR code review pass
- Resolve GitHub PR review threads via `gh api graphql` resolveReviewThread mutation
- PR prefix: OW (always — derived from project name Observability Watchdog)
- Never add "Co-Authored-By: Claude" line in commit messages
- Push to GitHub only after explicit user approval

## Frontend / Dashboard Testing
- Always test dashboard/UI changes with Playwright MCP (mcp__plugin_playwright_playwright__*)
- Do NOT use Chrome DevTools MCP for UI testing — use Playwright MCP exclusively
- Playwright test sequence for dashboard:
  1. Start FastAPI: `uvicorn app.main:app --port 8000` (background)
  2. Start Streamlit: `streamlit run dashboard/app.py --server.port 8501` (background)
  3. Navigate to http://localhost:8501, take screenshot, verify all 5 sections render
  4. Test error states: stop API, reload, confirm graceful empty states show
  5. After Playwright tests pass → run code-reviewer → only then create PR

## Context Window
- Warn user proactively when context approaches ~80% capacity
- List all standing in-flight instructions before /compact runs so nothing is lost
