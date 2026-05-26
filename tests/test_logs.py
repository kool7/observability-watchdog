from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from httpx import AsyncClient

from app.models.log_entry import LogLevel

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _log_payload(**overrides):
    base = {
        "service_name": "auth-service",
        "level": "ERROR",
        "message": "Connection refused to DB",
    }
    base.update(overrides)
    return base


def _make_db_log(payload: dict):
    """Fake ORM object returned by the DB layer."""
    obj = MagicMock()
    obj.id = uuid4()
    obj.service_name = payload["service_name"]
    obj.level = payload["level"]
    obj.message = payload["message"]
    obj.timestamp = datetime.now(timezone.utc)
    obj.metadata_ = payload.get("metadata")
    return obj


# ---------------------------------------------------------------------------
# POST /logs/ingest — single entry
# ---------------------------------------------------------------------------


class TestIngestSingle:
    async def test_ingest_returns_201(self, client: AsyncClient):
        fake = _make_db_log(_log_payload())
        with patch("app.routers.logs.create_log_entry", new_callable=AsyncMock) as m:
            m.return_value = fake
            response = await client.post("/logs/ingest", json=_log_payload())
        assert response.status_code == 201

    async def test_ingest_response_has_id(self, client: AsyncClient):
        fake = _make_db_log(_log_payload())
        with patch("app.routers.logs.create_log_entry", new_callable=AsyncMock) as m:
            m.return_value = fake
            response = await client.post("/logs/ingest", json=_log_payload())
        data = response.json()
        assert "id" in data
        assert data["service_name"] == "auth-service"
        assert data["level"] == "ERROR"

    async def test_ingest_invalid_level_returns_422(self, client: AsyncClient):
        response = await client.post("/logs/ingest", json=_log_payload(level="VERBOSE"))
        assert response.status_code == 422

    async def test_ingest_missing_service_name_returns_422(self, client: AsyncClient):
        response = await client.post(
            "/logs/ingest",
            json={"level": "ERROR", "message": "test"},
        )
        assert response.status_code == 422

    async def test_ingest_with_metadata(self, client: AsyncClient):
        payload = _log_payload(metadata={"request_id": "abc-123"})
        fake = _make_db_log(payload)
        with patch("app.routers.logs.create_log_entry", new_callable=AsyncMock) as m:
            m.return_value = fake
            response = await client.post("/logs/ingest", json=payload)
        assert response.status_code == 201


# ---------------------------------------------------------------------------
# POST /logs/ingest — batch
# ---------------------------------------------------------------------------


class TestIngestBatch:
    async def test_batch_ingest_returns_201(self, client: AsyncClient):
        payloads = [_log_payload(), _log_payload(level="INFO", message="ok")]
        fakes = [_make_db_log(p) for p in payloads]
        with patch(
            "app.routers.logs.create_log_entries_bulk", new_callable=AsyncMock
        ) as m:
            m.return_value = fakes
            response = await client.post("/logs/ingest", json=payloads)
        assert response.status_code == 201

    async def test_batch_ingest_returns_list(self, client: AsyncClient):
        payloads = [_log_payload(), _log_payload(level="WARN", message="slow")]
        fakes = [_make_db_log(p) for p in payloads]
        with patch(
            "app.routers.logs.create_log_entries_bulk", new_callable=AsyncMock
        ) as m:
            m.return_value = fakes
            response = await client.post("/logs/ingest", json=payloads)
        assert isinstance(response.json(), list)
        assert len(response.json()) == 2


# ---------------------------------------------------------------------------
# GET /logs
# ---------------------------------------------------------------------------


class TestGetLogs:
    async def test_get_logs_returns_200(self, client: AsyncClient):
        with patch("app.routers.logs.list_log_entries", new_callable=AsyncMock) as m:
            m.return_value = []
            response = await client.get("/logs")
        assert response.status_code == 200

    async def test_get_logs_returns_list(self, client: AsyncClient):
        fake = _make_db_log(_log_payload())
        with patch("app.routers.logs.list_log_entries", new_callable=AsyncMock) as m:
            m.return_value = [fake]
            response = await client.get("/logs")
        assert isinstance(response.json(), list)
        assert len(response.json()) == 1

    async def test_get_logs_filter_by_level(self, client: AsyncClient):
        with patch("app.routers.logs.list_log_entries", new_callable=AsyncMock) as m:
            m.return_value = []
            response = await client.get("/logs?level=ERROR")
        assert response.status_code == 200
        _, kwargs = m.call_args
        assert kwargs.get("level") == LogLevel.ERROR

    async def test_get_logs_invalid_level_returns_422(self, client: AsyncClient):
        response = await client.get("/logs?level=NONSENSE")
        assert response.status_code == 422

    async def test_get_logs_filter_by_service(self, client: AsyncClient):
        with patch("app.routers.logs.list_log_entries", new_callable=AsyncMock) as m:
            m.return_value = []
            response = await client.get("/logs?service_name=auth-service")
        assert response.status_code == 200
        _, kwargs = m.call_args
        assert kwargs.get("service_name") == "auth-service"

    async def test_get_logs_limit_forwarded(self, client: AsyncClient):
        with patch("app.routers.logs.list_log_entries", new_callable=AsyncMock) as m:
            m.return_value = []
            response = await client.get("/logs?limit=5")
        assert response.status_code == 200
        _, kwargs = m.call_args
        assert kwargs.get("limit") == 5

    async def test_get_logs_since_forwarded(self, client: AsyncClient):
        ts = "2025-01-01T00:00:00Z"
        with patch("app.routers.logs.list_log_entries", new_callable=AsyncMock) as m:
            m.return_value = []
            response = await client.get(f"/logs?since={ts}")
        assert response.status_code == 200
        _, kwargs = m.call_args
        assert kwargs.get("since") is not None

    async def test_get_logs_until_forwarded(self, client: AsyncClient):
        ts = "2025-12-31T23:59:59Z"
        with patch("app.routers.logs.list_log_entries", new_callable=AsyncMock) as m:
            m.return_value = []
            response = await client.get(f"/logs?until={ts}")
        assert response.status_code == 200
        _, kwargs = m.call_args
        assert kwargs.get("until") is not None


# ---------------------------------------------------------------------------
# GET /logs/{id}
# ---------------------------------------------------------------------------


class TestGetLogById:
    async def test_get_by_id_returns_200(self, client: AsyncClient):
        fake = _make_db_log(_log_payload())
        with patch("app.routers.logs.get_log_entry", new_callable=AsyncMock) as m:
            m.return_value = fake
            response = await client.get(f"/logs/{fake.id}")
        assert response.status_code == 200

    async def test_get_by_id_not_found_returns_404(self, client: AsyncClient):
        with patch("app.routers.logs.get_log_entry", new_callable=AsyncMock) as m:
            m.return_value = None
            response = await client.get(f"/logs/{uuid4()}")
        assert response.status_code == 404

    async def test_get_by_invalid_uuid_returns_422(self, client: AsyncClient):
        response = await client.get("/logs/not-a-uuid")
        assert response.status_code == 422
