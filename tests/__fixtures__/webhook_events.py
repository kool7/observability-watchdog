"""Faker-based factory for WebhookEvent-shaped mock objects."""

import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock

from faker import Faker

fake = Faker()


def make_webhook_event(**overrides) -> MagicMock:
    ev = MagicMock()
    ev.id = uuid.UUID(fake.uuid4())
    ev.anomaly_id = uuid.UUID(fake.uuid4())
    ev.fired_at = datetime.now(timezone.utc)
    ev.payload = {
        "service_name": f"{fake.word()}-service",
        "severity": fake.random_element(["LOW", "MEDIUM", "HIGH", "CRITICAL"]),
        "error_count": fake.random_int(min=5, max=100),
    }
    ev.response_status = 200
    for key, value in overrides.items():
        setattr(ev, key, value)
    return ev
