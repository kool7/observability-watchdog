"""
Tests for anomaly persistence service and ingest-triggered detection.
DB layer is mocked throughout.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from httpx import AsyncClient

from app.models.anomaly import Severity
from app.services.anomaly_detector import AnomalyResult

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_NOW = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)


def _make_anomaly_result() -> AnomalyResult:
    from datetime import timedelta

    return AnomalyResult(
        service_name="auth-service",
        detected_at=_NOW,
        window_start=_NOW - timedelta(minutes=5),
        window_end=_NOW,
        error_count=30,
        z_score=4.5,
        threshold_breached=2.0,
        severity=Severity.HIGH,
    )


def _make_db_anomaly():
    obj = MagicMock()
    obj.id = uuid4()
    obj.service_name = "auth-service"
    obj.detected_at = _NOW
    obj.window_start = _NOW
    obj.window_end = _NOW
    obj.error_count = 30
    obj.z_score = 4.5
    obj.threshold_breached = 2.0
    obj.severity = Severity.HIGH
    obj.ai_narrative = None
    obj.webhook_fired = False
    return obj


# ---------------------------------------------------------------------------
# AnomalyService.save
# ---------------------------------------------------------------------------


class TestAnomalySave:
    async def test_save_returns_orm_object(self):
        from app.services.anomaly_service import save_anomaly

        mock_db = AsyncMock()
        mock_db.refresh = AsyncMock()
        result = _make_anomaly_result()

        await save_anomaly(mock_db, result)

        mock_db.add.assert_called_once()
        mock_db.commit.assert_awaited_once()
        mock_db.refresh.assert_awaited_once()

    async def test_save_maps_all_fields(self):
        from app.services.anomaly_service import save_anomaly

        mock_db = AsyncMock()
        mock_db.refresh = AsyncMock()

        result = _make_anomaly_result()
        await save_anomaly(mock_db, result)

        added = mock_db.add.call_args[0][0]
        assert added.service_name == "auth-service"
        assert added.z_score == 4.5
        assert added.error_count == 30
        assert added.severity == Severity.HIGH
        assert added.threshold_breached == 2.0
        assert added.webhook_fired is False


# ---------------------------------------------------------------------------
# Ingest triggers anomaly detection
# ---------------------------------------------------------------------------


class TestIngestTriggersDetection:
    async def test_no_anomaly_when_detector_returns_none(self, client: AsyncClient):
        """Ingest should succeed even when no anomaly is detected."""
        from datetime import datetime, timezone
        from unittest.mock import MagicMock
        from uuid import uuid4

        fake_log = MagicMock()
        fake_log.id = uuid4()
        fake_log.service_name = "svc"
        fake_log.level = "ERROR"
        fake_log.message = "test"
        fake_log.timestamp = datetime.now(timezone.utc)
        fake_log.metadata_ = None

        with (
            patch(
                "app.routers.logs.create_log_entry", new_callable=AsyncMock
            ) as mock_create,
            patch(
                "app.routers.logs.run_anomaly_check", new_callable=AsyncMock
            ) as mock_check,
        ):
            mock_create.return_value = fake_log
            mock_check.return_value = None
            response = await client.post(
                "/logs/ingest",
                json={"service_name": "svc", "level": "ERROR", "message": "test"},
            )

        assert response.status_code == 201
        mock_check.assert_awaited_once()

    async def test_anomaly_saved_when_detector_fires(self, client: AsyncClient):
        """When detector returns an anomaly, it should be persisted."""
        from datetime import datetime, timezone
        from unittest.mock import MagicMock
        from uuid import uuid4

        fake_log = MagicMock()
        fake_log.id = uuid4()
        fake_log.service_name = "auth-service"
        fake_log.level = "ERROR"
        fake_log.message = "DB timeout"
        fake_log.timestamp = datetime.now(timezone.utc)
        fake_log.metadata_ = None

        fake_anomaly = _make_db_anomaly()

        with (
            patch(
                "app.routers.logs.create_log_entry", new_callable=AsyncMock
            ) as mock_create,
            patch(
                "app.routers.logs.run_anomaly_check", new_callable=AsyncMock
            ) as mock_check,
        ):
            mock_create.return_value = fake_log
            mock_check.return_value = fake_anomaly
            response = await client.post(
                "/logs/ingest",
                json={
                    "service_name": "auth-service",
                    "level": "ERROR",
                    "message": "DB timeout",
                },
            )

        assert response.status_code == 201
        mock_check.assert_awaited_once()
