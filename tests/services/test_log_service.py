"""Tests for log_service — create, bulk-create, list, get."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from app.models.log_entry import LogLevel
from app.schemas.log_entry import LogEntryCreate


def _make_db():
    db = AsyncMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.add = MagicMock()
    db.add_all = MagicMock()
    db.execute = AsyncMock()
    return db


def _make_schema(**overrides) -> LogEntryCreate:
    defaults = dict(
        service_name="auth-service",
        level=LogLevel.ERROR,
        message="Something went wrong",
        timestamp=datetime.now(timezone.utc),
    )
    defaults.update(overrides)
    return LogEntryCreate(**defaults)


def _make_orm_entry(**overrides):
    entry = MagicMock()
    entry.id = uuid4()
    entry.service_name = "auth-service"
    entry.level = LogLevel.ERROR
    entry.message = "Something went wrong"
    entry.timestamp = datetime.now(timezone.utc)
    entry.metadata_ = None
    for k, v in overrides.items():
        setattr(entry, k, v)
    return entry


class TestCreateLogEntry:
    async def test_adds_and_commits(self):
        from app.services.log_service import create_log_entry

        db = _make_db()
        schema = _make_schema()
        await create_log_entry(db, schema)

        db.add.assert_called_once()
        db.commit.assert_awaited_once()
        db.refresh.assert_awaited_once()

    async def test_maps_fields_to_orm(self):
        from app.services.log_service import create_log_entry

        db = _make_db()
        schema = _make_schema(service_name="payment-service", level=LogLevel.WARN)
        await create_log_entry(db, schema)

        added = db.add.call_args[0][0]
        assert added.service_name == "payment-service"
        assert added.level == LogLevel.WARN
        assert added.message == "Something went wrong"

    async def test_metadata_mapped(self):
        from app.services.log_service import create_log_entry

        db = _make_db()
        schema = _make_schema()
        schema.metadata = {"key": "val"}
        await create_log_entry(db, schema)

        added = db.add.call_args[0][0]
        assert added.metadata_ == {"key": "val"}


class TestCreateLogEntriesBulk:
    async def test_adds_all_and_commits(self):
        from app.services.log_service import create_log_entries_bulk

        db = _make_db()
        schemas = [_make_schema(service_name=f"svc-{i}") for i in range(3)]
        await create_log_entries_bulk(db, schemas)

        db.add_all.assert_called_once()
        added = db.add_all.call_args[0][0]
        assert len(added) == 3
        db.commit.assert_awaited_once()

    async def test_refreshes_each_entry(self):
        from app.services.log_service import create_log_entries_bulk

        db = _make_db()
        schemas = [_make_schema() for _ in range(2)]
        await create_log_entries_bulk(db, schemas)

        assert db.refresh.await_count == 2

    async def test_empty_list_returns_empty(self):
        from app.services.log_service import create_log_entries_bulk

        db = _make_db()
        result = await create_log_entries_bulk(db, [])

        assert result == []
        db.add_all.assert_called_once_with([])


class TestListLogEntries:
    async def _run_list(self, db, **kwargs):
        from app.services.log_service import list_log_entries

        return await list_log_entries(db, **kwargs)

    def _mock_result(self, db, entries):
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = entries
        db.execute.return_value = mock_result

    async def test_returns_entries(self):
        db = _make_db()
        entries = [_make_orm_entry(), _make_orm_entry()]
        self._mock_result(db, entries)

        result = await self._run_list(db)
        assert len(result) == 2

    async def test_filters_applied_without_error(self):
        db = _make_db()
        self._mock_result(db, [])

        result = await self._run_list(
            db,
            level=LogLevel.ERROR,
            service_name="auth-service",
            since=datetime(2025, 1, 1, tzinfo=timezone.utc),
            until=datetime(2025, 12, 31, tzinfo=timezone.utc),
            limit=10,
        )
        assert result == []
        db.execute.assert_awaited_once()

    async def test_limit_capped_at_1000(self):
        from app.services.log_service import list_log_entries

        db = _make_db()
        self._mock_result(db, [])
        await list_log_entries(db, limit=9999)
        db.execute.assert_awaited_once()


class TestGetLogEntry:
    async def test_returns_entry_when_found(self):
        from app.services.log_service import get_log_entry

        db = _make_db()
        entry = _make_orm_entry()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = entry
        db.execute.return_value = mock_result

        result = await get_log_entry(db, entry.id)
        assert result is entry

    async def test_returns_none_when_not_found(self):
        from app.services.log_service import get_log_entry

        db = _make_db()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        db.execute.return_value = mock_result

        result = await get_log_entry(db, uuid4())
        assert result is None
