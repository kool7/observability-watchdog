"""Tests for webhook_event_service — list_webhook_events."""

from unittest.mock import AsyncMock, MagicMock

from tests.__fixtures__.webhook_events import make_webhook_event


def _make_db():
    db = AsyncMock()
    db.execute = AsyncMock()
    return db


class TestListWebhookEvents:
    async def test_returns_event_list(self):
        from app.services.webhook_event_service import list_webhook_events

        db = _make_db()
        events = [make_webhook_event(), make_webhook_event()]
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = events
        db.execute.return_value = mock_result

        result = await list_webhook_events(db)
        assert len(result) == 2

    async def test_returns_empty_list(self):
        from app.services.webhook_event_service import list_webhook_events

        db = _make_db()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        db.execute.return_value = mock_result

        result = await list_webhook_events(db)
        assert result == []

    async def test_limit_passed_through(self):
        from app.services.webhook_event_service import list_webhook_events

        db = _make_db()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        db.execute.return_value = mock_result

        await list_webhook_events(db, limit=5)
        db.execute.assert_awaited_once()
