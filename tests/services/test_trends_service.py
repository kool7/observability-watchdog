"""Tests for trends_service — get_log_trends with mocked DB."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock


def _make_db():
    db = AsyncMock()
    db.execute = AsyncMock()
    return db


def _make_row(bucket, service, errors=0, warns=0, infos=0):
    row = MagicMock()
    row.bucket = bucket
    row.service_name = service
    row.error_count = errors
    row.warn_count = warns
    row.info_count = infos
    return row


class TestGetLogTrends:
    async def test_returns_empty_list_when_no_rows(self):
        from app.services.trends_service import get_log_trends

        db = _make_db()
        mock_result = MagicMock()
        mock_result.all.return_value = []
        db.execute.return_value = mock_result

        result = await get_log_trends(db)
        assert result == []

    async def test_maps_row_to_trend_bucket_response(self):
        from app.schemas.trends import TrendBucketResponse
        from app.services.trends_service import get_log_trends

        db = _make_db()
        now = datetime.now(timezone.utc)
        row = _make_row(now, "api-gateway", errors=5, warns=2, infos=10)
        mock_result = MagicMock()
        mock_result.all.return_value = [row]
        db.execute.return_value = mock_result

        result = await get_log_trends(db)

        assert len(result) == 1
        assert isinstance(result[0], TrendBucketResponse)
        assert result[0].service_name == "api-gateway"
        assert result[0].error_count == 5
        assert result[0].warn_count == 2
        assert result[0].info_count == 10
        assert result[0].bucket == now

    async def test_returns_multiple_rows(self):
        from app.services.trends_service import get_log_trends

        db = _make_db()
        now = datetime.now(timezone.utc)
        rows = [
            _make_row(now, "svc-a", errors=1),
            _make_row(now, "svc-b", errors=3),
        ]
        mock_result = MagicMock()
        mock_result.all.return_value = rows
        db.execute.return_value = mock_result

        result = await get_log_trends(db)
        assert len(result) == 2
        assert {r.service_name for r in result} == {"svc-a", "svc-b"}

    async def test_service_name_filter_executes_query(self):
        from app.services.trends_service import get_log_trends

        db = _make_db()
        mock_result = MagicMock()
        mock_result.all.return_value = []
        db.execute.return_value = mock_result

        await get_log_trends(db, hours=2, service_name="payment-service")
        db.execute.assert_awaited_once()

    async def test_counts_cast_to_int(self):
        from app.services.trends_service import get_log_trends

        db = _make_db()
        now = datetime.now(timezone.utc)
        row = _make_row(now, "svc", errors=7, warns=3, infos=15)
        mock_result = MagicMock()
        mock_result.all.return_value = [row]
        db.execute.return_value = mock_result

        result = await get_log_trends(db)
        assert isinstance(result[0].error_count, int)
        assert isinstance(result[0].warn_count, int)
        assert isinstance(result[0].info_count, int)
