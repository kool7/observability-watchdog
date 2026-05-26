import logging
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.rate_limiter import limiter
from app.models.log_entry import LogLevel
from app.schemas.log_entry import LogEntryCreate, LogEntryResponse
from app.services.anomaly_service import run_anomaly_check
from app.services.log_service import (
    create_log_entries_bulk,
    create_log_entry,
    get_log_entry,
    list_log_entries,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/logs", tags=["logs"])


@router.post(
    "/ingest",
    response_model=LogEntryResponse | list[LogEntryResponse],
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit("10/minute")
async def ingest_logs(
    request: Request,
    payload: LogEntryCreate | list[LogEntryCreate],
    db: AsyncSession = Depends(get_db),
):
    if isinstance(payload, list):
        result = await create_log_entries_bulk(db, payload)
        for svc in {item.service_name for item in payload}:
            try:
                await run_anomaly_check(db, svc)
            except Exception:
                logger.exception("anomaly check failed for service %s", svc)
        return result

    entry = await create_log_entry(db, payload)
    try:
        await run_anomaly_check(db, payload.service_name)
    except Exception:
        logger.exception("anomaly check failed for service %s", payload.service_name)
    return entry


@router.get("", response_model=list[LogEntryResponse])
async def get_logs(
    level: LogLevel | None = None,
    service_name: str | None = None,
    since: datetime | None = None,
    until: datetime | None = None,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
):
    return await list_log_entries(
        db,
        level=level,
        service_name=service_name,
        since=since,
        until=until,
        limit=limit,
    )


@router.get("/{entry_id}", response_model=LogEntryResponse)
async def get_log(entry_id: UUID, db: AsyncSession = Depends(get_db)):
    entry = await get_log_entry(db, entry_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="Log entry not found")
    return entry
