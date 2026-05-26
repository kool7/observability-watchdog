"""Tests for the webhook router — POST /webhook/receive and GET /webhook/events."""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from httpx import ASGITransport, AsyncClient

from app.main import app


def _fake_event():
    ev = MagicMock()
    ev.id = uuid.uuid4()
    ev.anomaly_id = uuid.uuid4()
    ev.fired_at = datetime.now(timezone.utc)
    ev.payload = {"service_name": "auth-service", "severity": "HIGH"}
    ev.response_status = 200
    return ev


# ---------------------------------------------------------------------------
# POST /webhook/receive
# ---------------------------------------------------------------------------


class TestWebhookReceive:
    async def test_returns_200_with_received_true(self):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/webhook/receive", json={"service": "auth", "event": "anomaly"}
            )

        assert resp.status_code == 200
        assert resp.json() == {"received": True}

    async def test_accepts_any_json_payload(self):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/webhook/receive",
                json={"nested": {"a": 1, "b": [1, 2, 3]}, "flag": True},
            )

        assert resp.status_code == 200

    async def test_accepts_empty_payload(self):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post("/webhook/receive", json={})

        assert resp.status_code == 200

    async def test_accepts_non_json_body_without_crashing(self):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/webhook/receive",
                content=b"not-json-at-all",
                headers={"content-type": "text/plain"},
            )

        assert resp.status_code == 200
        assert resp.json() == {"received": True}


# ---------------------------------------------------------------------------
# GET /webhook/events
# ---------------------------------------------------------------------------


class TestWebhookEvents:
    async def test_returns_list_of_events(self):
        with patch(
            "app.routers.webhooks.list_webhook_events", new_callable=AsyncMock
        ) as mock_list:
            mock_list.return_value = [_fake_event()]

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.get("/webhook/events")

        assert resp.status_code == 200
        body = resp.json()
        assert isinstance(body, list)
        assert len(body) == 1
        assert body[0]["response_status"] == 200

    async def test_returns_empty_list_when_no_events(self):
        with patch(
            "app.routers.webhooks.list_webhook_events", new_callable=AsyncMock
        ) as mock_list:
            mock_list.return_value = []

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.get("/webhook/events")

        assert resp.status_code == 200
        assert resp.json() == []

    async def test_event_has_required_fields(self):
        event = _fake_event()
        with patch(
            "app.routers.webhooks.list_webhook_events", new_callable=AsyncMock
        ) as mock_list:
            mock_list.return_value = [event]

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.get("/webhook/events")

        item = resp.json()[0]
        assert "id" in item
        assert "anomaly_id" in item
        assert "fired_at" in item
        assert "payload" in item
        assert "response_status" in item
