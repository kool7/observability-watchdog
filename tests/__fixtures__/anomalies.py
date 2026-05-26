"""Faker-based factory for Anomaly ORM objects."""

import uuid
from datetime import datetime, timedelta, timezone

from faker import Faker

from app.models.anomaly import Anomaly, Severity

fake = Faker()


def make_anomaly(**overrides) -> Anomaly:
    now = datetime.now(timezone.utc)
    defaults = dict(
        id=uuid.UUID(fake.uuid4()),
        service_name=f"{fake.word()}-service",
        detected_at=now,
        window_start=now - timedelta(minutes=5),
        window_end=now,
        error_count=fake.random_int(min=10, max=100),
        z_score=round(fake.pyfloat(min_value=2.1, max_value=8.0, right_digits=2), 2),
        threshold_breached=2.0,
        severity=fake.random_element(list(Severity)),
        ai_narrative=fake.sentence(),
        webhook_fired=False,
    )
    defaults.update(overrides)
    return Anomaly(**defaults)
