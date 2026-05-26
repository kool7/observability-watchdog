"""DB queries for WebhookEvent records."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.webhook_event import WebhookEvent


async def list_webhook_events(db: AsyncSession, limit: int = 50) -> list[WebhookEvent]:
    stmt = select(WebhookEvent).order_by(WebhookEvent.fired_at.desc()).limit(limit)
    result = await db.execute(stmt)
    return list(result.scalars().all())
