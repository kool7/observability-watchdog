"""Fire simulated webhook alerts when an anomaly is detected."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.webhook_event import WebhookEvent

if TYPE_CHECKING:
    from app.models.anomaly import Anomaly

logger = logging.getLogger(__name__)


def _build_payload(anomaly: Anomaly) -> dict:
    return {
        "anomaly_id": str(anomaly.id),
        "service_name": anomaly.service_name,
        "severity": anomaly.severity.value,
        "z_score": anomaly.z_score,
        "error_count": anomaly.error_count,
        "detected_at": anomaly.detected_at.isoformat(),
        "ai_narrative": anomaly.ai_narrative,
    }


async def fire(anomaly: Anomaly, db: AsyncSession) -> None:
    """POST anomaly payload to WEBHOOK_URL and persist the event record."""
    payload = _build_payload(anomaly)
    status_code = 0

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                settings.webhook_url, json=payload, timeout=5.0
            )
            status_code = response.status_code
    except Exception:
        logger.exception(
            "Webhook delivery failed for anomaly %s service %s",
            anomaly.id,
            anomaly.service_name,
        )

    event = WebhookEvent(
        anomaly_id=anomaly.id,
        fired_at=datetime.now(timezone.utc),
        payload=payload,
        response_status=status_code,
    )
    db.add(event)
    # Only mark as fired when the target confirmed receipt (2xx response)
    if 200 <= status_code < 300:
        anomaly.webhook_fired = True
    await db.commit()
    await db.refresh(event)

    logger.info(
        "Webhook fired for anomaly %s → %s (status %d)",
        anomaly.id,
        settings.webhook_url,
        status_code,
    )
