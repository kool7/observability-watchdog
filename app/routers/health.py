from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.schemas.trends import TrendBucketResponse
from app.services.trends_service import get_log_trends

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check():
    return {"status": "ok", "version": settings.version}


@router.get("/health/trends", response_model=list[TrendBucketResponse])
async def health_trends(
    service_name: str | None = Query(default=None, min_length=1),
    hours: int = Query(default=6, ge=1, le=168),
    db: AsyncSession = Depends(get_db),
):
    """Return per-service log counts in 5-minute buckets over the past N hours."""
    return await get_log_trends(db, hours=hours, service_name=service_name)
