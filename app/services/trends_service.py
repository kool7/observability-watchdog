"""Aggregate log counts into 5-minute time-series buckets."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import BigInteger, case, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.log_entry import LogEntry, LogLevel


@dataclass
class TrendBucket:
    bucket: datetime
    service_name: str
    error_count: int
    warn_count: int
    info_count: int


async def get_log_trends(
    db: AsyncSession,
    hours: int = 6,
    service_name: str | None = None,
) -> list[TrendBucket]:
    """Return per-service error/warn/info counts in 5-minute buckets."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)

    # Epoch arithmetic for 5-min bucketing. BigInteger prevents 32-bit overflow
    # (~2038 boundary). PostgreSQL allows referencing SELECT aliases in GROUP BY.
    bucket_expr = func.to_timestamp(
        (func.extract("epoch", LogEntry.timestamp).cast(BigInteger) / 300) * 300
    ).label("bucket")

    stmt = select(
        bucket_expr,
        LogEntry.service_name,
        func.sum(case((LogEntry.level == LogLevel.ERROR, 1), else_=0)).label(
            "error_count"
        ),
        func.sum(case((LogEntry.level == LogLevel.WARN, 1), else_=0)).label(
            "warn_count"
        ),
        func.sum(case((LogEntry.level == LogLevel.INFO, 1), else_=0)).label(
            "info_count"
        ),
    ).where(LogEntry.timestamp >= cutoff)

    if service_name:
        stmt = stmt.where(LogEntry.service_name == service_name)

    stmt = stmt.group_by(text("bucket"), LogEntry.service_name).order_by(text("bucket"))

    result = await db.execute(stmt)
    rows = result.all()

    return [
        TrendBucket(
            bucket=row.bucket,
            service_name=row.service_name,
            error_count=int(row.error_count),
            warn_count=int(row.warn_count),
            info_count=int(row.info_count),
        )
        for row in rows
    ]
