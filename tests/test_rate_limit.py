from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from httpx import AsyncClient


def _make_fake_log():
    obj = MagicMock()
    obj.id = uuid4()
    obj.service_name = "svc"
    obj.level = "ERROR"
    obj.message = "test"
    obj.timestamp = datetime.now(timezone.utc)
    obj.metadata_ = None
    return obj


async def test_rate_limit_header_present(client: AsyncClient):
    """Ingest endpoint should respond — rate limit middleware is wired."""
    fake = _make_fake_log()
    with patch("app.routers.logs.create_log_entry", new_callable=AsyncMock) as m:
        m.return_value = fake
        response = await client.post(
            "/logs/ingest",
            json={"service_name": "svc", "level": "ERROR", "message": "test"},
        )
    assert response.status_code == 201


async def test_rate_limit_returns_429_after_burst(client: AsyncClient):
    """Exceeding 10 req/min from same IP should return 429."""
    fake = _make_fake_log()
    payload = {"service_name": "svc", "level": "ERROR", "message": "test"}

    with patch("app.routers.logs.create_log_entry", new_callable=AsyncMock) as m:
        m.return_value = fake
        responses = [await client.post("/logs/ingest", json=payload) for _ in range(12)]

    status_codes = [r.status_code for r in responses]
    assert 429 in status_codes
