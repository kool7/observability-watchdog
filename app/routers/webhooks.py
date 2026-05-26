"""Webhook router — receive inbound alerts and expose fired event history."""

import logging

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.webhook_event import WebhookEventResponse
from app.services.webhook_event_service import list_webhook_events

logger = logging.getLogger(__name__)
router = APIRouter(tags=["webhooks"])


@router.post("/webhook/receive")
async def receive_webhook(request: Request) -> dict:
    """Accept any inbound webhook payload and acknowledge it."""
    try:
        body = await request.json()
    except Exception:
        body = {}
    logger.info("Webhook received: %s", body)
    return {"received": True}


@router.get("/webhook/events", response_model=list[WebhookEventResponse])
async def get_webhook_events(
    db: AsyncSession = Depends(get_db),
):
    """Return the last 50 fired webhook events, newest first."""
    return await list_webhook_events(db)
