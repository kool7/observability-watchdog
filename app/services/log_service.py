from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.log_entry import LogEntry
from app.schemas.log_entry import LogEntryCreate


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


async def list_log_entries(
    db: AsyncSession,
    level: str | None = None,
    service_name: str | None = None,
    since: datetime | None = None,
    until: datetime | None = None,
    limit: int = 100,
) -> list[LogEntry]:
    stmt = select(LogEntry).order_by(LogEntry.timestamp.desc()).limit(limit)
    if level:
        stmt = stmt.where(LogEntry.level == level)
    if service_name:
        stmt = stmt.where(LogEntry.service_name == service_name)
    if since:
        stmt = stmt.where(LogEntry.timestamp >= since)
    if until:
        stmt = stmt.where(LogEntry.timestamp <= until)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_log_entry(db: AsyncSession, entry_id: UUID) -> LogEntry | None:
    result = await db.execute(select(LogEntry).where(LogEntry.id == entry_id))
    return result.scalar_one_or_none()
