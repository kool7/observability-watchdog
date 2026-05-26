"""Tests for the webhook firing service. All HTTP calls are mocked."""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx

from tests.__fixtures__.anomalies import make_anomaly


def _make_db():
    db = AsyncMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.add = MagicMock()
    db.execute = AsyncMock()
    return db


# ---------------------------------------------------------------------------
# fire() — happy path
# ---------------------------------------------------------------------------


class TestFireWebhook:
    async def test_creates_webhook_event_record(self):
        from app.services.webhook_service import fire

        anomaly = make_anomaly()
        db = _make_db()

        mock_response = MagicMock()
        mock_response.status_code = 200

        with patch("app.services.webhook_service.httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_cls.return_value = mock_client

            await fire(anomaly, db)

        db.add.assert_called_once()
        added = db.add.call_args[0][0]
        from app.models.webhook_event import WebhookEvent

        assert isinstance(added, WebhookEvent)
        assert added.anomaly_id == anomaly.id
        assert added.response_status == 200

    async def test_sets_webhook_fired_true(self):
        from app.services.webhook_service import fire

        anomaly = make_anomaly()
        db = _make_db()

        mock_response = MagicMock()
        mock_response.status_code = 200

        with patch("app.services.webhook_service.httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_cls.return_value = mock_client

            await fire(anomaly, db)

        assert anomaly.webhook_fired is True

    async def test_payload_contains_anomaly_fields(self):
        from app.services.webhook_service import fire

        anomaly = make_anomaly(service_name="payment-service", error_count=50)
        db = _make_db()

        mock_response = MagicMock()
        mock_response.status_code = 200
        posted_json = {}

        async def capture_post(url, json, timeout):
            posted_json.update(json)
            return mock_response

        with patch("app.services.webhook_service.httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.post = capture_post
            mock_cls.return_value = mock_client

            await fire(anomaly, db)

        assert posted_json["service_name"] == "payment-service"
        assert posted_json["error_count"] == 50
        assert "severity" in posted_json
        assert "z_score" in posted_json

    async def test_records_response_status_code(self):
        from app.services.webhook_service import fire

        anomaly = make_anomaly()
        db = _make_db()

        mock_response = MagicMock()
        mock_response.status_code = 503

        with patch("app.services.webhook_service.httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_cls.return_value = mock_client

            await fire(anomaly, db)

        added = db.add.call_args[0][0]
        assert added.response_status == 503

    async def test_commits_after_save(self):
        from app.services.webhook_service import fire

        anomaly = make_anomaly()
        db = _make_db()

        mock_response = MagicMock()
        mock_response.status_code = 200

        with patch("app.services.webhook_service.httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_cls.return_value = mock_client

            await fire(anomaly, db)

        db.commit.assert_called()


# ---------------------------------------------------------------------------
# fire() — error resilience
# ---------------------------------------------------------------------------


class TestFireWebhookErrors:
    async def test_does_not_raise_on_http_error(self):
        from app.services.webhook_service import fire

        anomaly = make_anomaly()
        db = _make_db()

        with patch("app.services.webhook_service.httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.post = AsyncMock(
                side_effect=httpx.ConnectError("connection refused")
            )
            mock_cls.return_value = mock_client

            # must not raise
            await fire(anomaly, db)

    async def test_records_status_0_on_http_error(self):
        from app.services.webhook_service import fire

        anomaly = make_anomaly()
        db = _make_db()

        with patch("app.services.webhook_service.httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.post = AsyncMock(side_effect=httpx.TimeoutException("timeout"))
            mock_cls.return_value = mock_client

            await fire(anomaly, db)

        added = db.add.call_args[0][0]
        assert added.response_status == 0

    async def test_webhook_fired_not_set_on_5xx(self):
        from app.services.webhook_service import fire

        anomaly = make_anomaly()
        db = _make_db()

        mock_response = MagicMock()
        mock_response.status_code = 503

        with patch("app.services.webhook_service.httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_cls.return_value = mock_client

            await fire(anomaly, db)

        assert anomaly.webhook_fired is False

    async def test_webhook_fired_not_set_on_http_failure(self):
        from app.services.webhook_service import fire

        anomaly = make_anomaly()
        db = _make_db()

        with patch("app.services.webhook_service.httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.post = AsyncMock(
                side_effect=httpx.ConnectError("connection refused")
            )
            mock_cls.return_value = mock_client

            await fire(anomaly, db)

        assert anomaly.webhook_fired is False
