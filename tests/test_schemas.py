from datetime import datetime, timezone
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.models.anomaly import Severity
from app.models.log_entry import LogLevel


class TestLogEntrySchemas:
    def test_create_valid(self):
        from app.schemas.log_entry import LogEntryCreate

        entry = LogEntryCreate(
            service_name="auth-service",
            level=LogLevel.ERROR,
            message="Connection refused",
        )
        assert entry.service_name == "auth-service"
        assert entry.level == LogLevel.ERROR
        assert entry.timestamp is not None

    def test_create_timestamp_defaults_to_now(self):
        from app.schemas.log_entry import LogEntryCreate

        before = datetime.now(timezone.utc)
        entry = LogEntryCreate(service_name="svc", level=LogLevel.INFO, message="test")
        assert entry.timestamp >= before

    def test_create_invalid_level_rejected(self):
        from app.schemas.log_entry import LogEntryCreate

        with pytest.raises(ValidationError):
            LogEntryCreate(
                service_name="svc",
                level="VERBOSE",
                message="test",
            )

    def test_create_missing_service_name_rejected(self):
        from app.schemas.log_entry import LogEntryCreate

        with pytest.raises(ValidationError):
            LogEntryCreate(level=LogLevel.INFO, message="test")

    def test_response_from_orm(self):
        from app.schemas.log_entry import LogEntryResponse

        uid = uuid4()
        now = datetime.now(timezone.utc)

        class FakeORM:
            id = uid
            service_name = "svc"
            level = LogLevel.INFO
            message = "ok"
            timestamp = now
            metadata_ = None

        resp = LogEntryResponse.model_validate(FakeORM())
        assert resp.id == uid
        assert resp.service_name == "svc"


class TestAnomalySchemas:
    def test_response_from_orm(self):
        from app.schemas.anomaly import AnomalyResponse

        uid = uuid4()
        now = datetime.now(timezone.utc)

        class FakeORM:
            id = uid
            service_name = "api"
            detected_at = now
            window_start = now
            window_end = now
            error_count = 15
            z_score = 3.5
            threshold_breached = 2.0
            ai_narrative = "High error rate detected."
            severity = Severity.HIGH
            webhook_fired = False

        resp = AnomalyResponse.model_validate(FakeORM())
        assert resp.z_score == 3.5
        assert resp.severity == Severity.HIGH


class TestWebhookEventSchemas:
    def test_response_from_orm(self):
        from app.schemas.webhook_event import WebhookEventResponse

        uid = uuid4()
        anomaly_uid = uuid4()
        now = datetime.now(timezone.utc)

        class FakeORM:
            id = uid
            anomaly_id = anomaly_uid
            fired_at = now
            payload = {"service": "api", "z_score": 3.5}
            response_status = 200

        resp = WebhookEventResponse.model_validate(FakeORM())
        assert resp.response_status == 200
        assert resp.anomaly_id == anomaly_uid
