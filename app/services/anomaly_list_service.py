"""Read-side queries for persisted anomalies."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.middleware.error_handler import NotFoundError
from app.models.anomaly import Anomaly


async def list_anomalies(db: AsyncSession, limit: int = 50) -> list[Anomaly]:
    result = await db.execute(
        select(Anomaly).order_by(Anomaly.detected_at.desc()).limit(limit)
    )
    return list(result.scalars().all())


async def get_anomaly(db: AsyncSession, anomaly_id: UUID) -> Anomaly:
    result = await db.execute(select(Anomaly).where(Anomaly.id == anomaly_id))
    anomaly = result.scalar_one_or_none()
    if anomaly is None:
        raise NotFoundError(f"Anomaly {anomaly_id} not found")
    return anomaly
