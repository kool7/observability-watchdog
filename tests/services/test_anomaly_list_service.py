"""Tests for anomaly_list_service — list_anomalies and get_anomaly."""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from tests.__fixtures__.anomalies import make_anomaly


def _make_db():
    db = AsyncMock()
    db.execute = AsyncMock()
    return db


class TestListAnomalies:
    async def test_returns_anomaly_list(self):
        from app.services.anomaly_list_service import list_anomalies

        db = _make_db()
        anomalies = [make_anomaly(), make_anomaly()]
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = anomalies
        db.execute.return_value = mock_result

        result = await list_anomalies(db)
        assert len(result) == 2

    async def test_returns_empty_list(self):
        from app.services.anomaly_list_service import list_anomalies

        db = _make_db()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        db.execute.return_value = mock_result

        result = await list_anomalies(db)
        assert result == []

    async def test_limit_passed_through(self):
        from app.services.anomaly_list_service import list_anomalies

        db = _make_db()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        db.execute.return_value = mock_result

        await list_anomalies(db, limit=10)
        stmt = db.execute.call_args[0][0]
        assert "10" in str(stmt.compile(compile_kwargs={"literal_binds": True}))


class TestGetAnomaly:
    async def test_returns_anomaly_when_found(self):
        from app.services.anomaly_list_service import get_anomaly

        db = _make_db()
        anomaly = make_anomaly()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = anomaly
        db.execute.return_value = mock_result

        result = await get_anomaly(db, anomaly.id)
        assert result is anomaly

    async def test_raises_not_found_when_missing(self):
        from app.middleware.error_handler import NotFoundError
        from app.services.anomaly_list_service import get_anomaly

        db = _make_db()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        db.execute.return_value = mock_result

        with pytest.raises(NotFoundError):
            await get_anomaly(db, uuid4())
