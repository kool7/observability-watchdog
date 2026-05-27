from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.anomaly import Anomaly
from app.models.log_entry import LogEntry, LogLevel
from app.services.anomaly_detector import ZScoreDetector
from app.services.claude_service import generate_anomaly_narrative
from app.services.webhook_service import fire as fire_webhook

if TYPE_CHECKING:
    from app.services.anomaly_detector import AnomalyResult

logger = logging.getLogger(__name__)

_DETECTOR_Z_THRESHOLD = 2.0
_DETECTOR_WINDOW_MINUTES = 5
_DETECTOR_LOOKBACK_HOURS = 1
# Suppress duplicate anomalies for the same service within one detection window
_COOLDOWN_MINUTES = _DETECTOR_WINDOW_MINUTES


async def save_anomaly(
    db: AsyncSession, result: AnomalyResult, ai_narrative: str | None = None
) -> Anomaly:
    anomaly = Anomaly(
        service_name=result.service_name,
        detected_at=result.detected_at,
        window_start=result.window_start,
        window_end=result.window_end,
        error_count=result.error_count,
        z_score=result.z_score,
        threshold_breached=result.threshold_breached,
        severity=result.severity,
        ai_narrative=ai_narrative,
        webhook_fired=False,
        baseline_mean=(
            result.baseline_mean if result.baseline_mean is not None else None
        ),
    )
    db.add(anomaly)
    await db.commit()
    await db.refresh(anomaly)
    return anomaly


async def run_anomaly_check(db: AsyncSession, service_name: str) -> Anomaly | None:
    """Fetch recent ERROR timestamps for a service and run Z-score detection."""
    # Skip if an anomaly was already raised for this service within the cooldown window
    # to avoid duplicate detections from the same error spike.
    now = datetime.now(timezone.utc)
    cooldown_cutoff = now - timedelta(minutes=_COOLDOWN_MINUTES)
    recent = await db.execute(
        select(Anomaly.id)
        .where(
            and_(
                Anomaly.service_name == service_name,
                Anomaly.detected_at >= cooldown_cutoff,
            )
        )
        .limit(1)
    )
    if recent.scalar_one_or_none() is not None:
        return None

    detector = ZScoreDetector(
        window_minutes=_DETECTOR_WINDOW_MINUTES,
        z_threshold=_DETECTOR_Z_THRESHOLD,
        lookback_hours=_DETECTOR_LOOKBACK_HOURS,
    )

    cutoff = now - timedelta(hours=_DETECTOR_LOOKBACK_HOURS)

    log_stmt = select(LogEntry.timestamp).where(
        and_(
            LogEntry.service_name == service_name,
            LogEntry.level == LogLevel.ERROR,
            LogEntry.timestamp >= cutoff,
        )
    )
    result = await db.execute(log_stmt)
    error_timestamps = list(result.scalars().all())

    detection = detector.analyze(service_name, error_timestamps, at=now)
    if detection is None:
        return None

    narrative = await generate_anomaly_narrative(detection)
    anomaly = await save_anomaly(db, detection, ai_narrative=narrative)
    await fire_webhook(anomaly, db)
    return anomaly
