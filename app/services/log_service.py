from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.log_entry import LogEntry, LogLevel
from app.schemas.log_entry import LogEntryCreate

_MAX_LIMIT = 1000


async def create_log_entry(db: AsyncSession, data: LogEntryCreate) -> LogEntry:
    entry = LogEntry(
        service_name=data.service_name,
        level=data.level,
        message=data.message,
        timestamp=data.timestamp,
        metadata_=data.metadata,
    )
    db.add(entry)
    await db.commit()
    await db.refresh(entry)
    return entry


async def create_log_entries_bulk(
    db: AsyncSession, data: list[LogEntryCreate]
) -> list[LogEntry]:
    entries = [
        LogEntry(
            service_name=item.service_name,
            level=item.level,
            message=item.message,
            timestamp=item.timestamp,
            metadata_=item.metadata,
        )
        for item in data
    ]
    db.add_all(entries)
    await db.commit()
    # expire_on_commit=False means objects remain usable after commit without refresh
    return entries


async def list_log_entries(
    db: AsyncSession,
    level: LogLevel | None = None,
    service_name: str | None = None,
    since: datetime | None = None,
    until: datetime | None = None,
    limit: int = 100,
) -> list[LogEntry]:
    limit = min(limit, _MAX_LIMIT)
    stmt = select(LogEntry)
    if level:
        stmt = stmt.where(LogEntry.level == level)
    if service_name:
        stmt = stmt.where(LogEntry.service_name == service_name)
    if since:
        stmt = stmt.where(LogEntry.timestamp >= since)
    if until:
        stmt = stmt.where(LogEntry.timestamp <= until)
    stmt = stmt.order_by(LogEntry.timestamp.desc()).limit(limit)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_log_entry(db: AsyncSession, entry_id: UUID) -> LogEntry | None:
    result = await db.execute(select(LogEntry).where(LogEntry.id == entry_id))
    return result.scalar_one_or_none()
