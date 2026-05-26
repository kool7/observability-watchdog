"""
Tests for the Claude AI narrative generation service.
All tests mock the Anthropic client — no real API calls.
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from anthropic.types import TextBlock

from app.models.anomaly import Severity
from app.services.anomaly_detector import AnomalyResult

_NOW = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)


def _make_result(
    severity: Severity = Severity.HIGH, z_score: float = 4.5
) -> AnomalyResult:
    return AnomalyResult(
        service_name="auth-service",
        detected_at=_NOW,
        window_start=_NOW - timedelta(minutes=5),
        window_end=_NOW,
        error_count=30,
        z_score=z_score,
        threshold_breached=2.0,
        severity=severity,
    )


def _mock_anthropic_response(text: str) -> MagicMock:
    content_block = MagicMock(spec=TextBlock)
    content_block.text = text
    message = MagicMock()
    message.content = [content_block]
    return message


def _make_mock_client(response: MagicMock) -> AsyncMock:
    """Return an AsyncAnthropic-like mock whose messages.create returns `response`."""
    mock_client = AsyncMock()
    mock_client.messages.create = AsyncMock(return_value=response)
    return mock_client


def _make_failing_client(error: Exception) -> AsyncMock:
    mock_client = AsyncMock()
    mock_client.messages.create = AsyncMock(side_effect=error)
    return mock_client


# ---------------------------------------------------------------------------
# generate_anomaly_narrative
# ---------------------------------------------------------------------------


class TestGenerateAnomalyNarrative:
    async def test_returns_string(self):
        from app.services.claude_service import generate_anomaly_narrative

        mock_client = _make_mock_client(_mock_anthropic_response("spike detected."))
        with patch("app.services.claude_service._get_client", return_value=mock_client):
            result = await generate_anomaly_narrative(_make_result())

        assert isinstance(result, str)
        assert len(result) > 0

    async def test_passes_correct_model(self):
        from app.services.claude_service import generate_anomaly_narrative

        mock_client = _make_mock_client(_mock_anthropic_response("narrative text"))
        with patch("app.services.claude_service._get_client", return_value=mock_client):
            await generate_anomaly_narrative(_make_result())

        call_kwargs = mock_client.messages.create.call_args.kwargs
        assert call_kwargs["model"] == "claude-sonnet-4-6"

    async def test_passes_system_prompt(self):
        from app.prompts import ANOMALY_SYSTEM
        from app.services.claude_service import generate_anomaly_narrative

        mock_client = _make_mock_client(_mock_anthropic_response("narrative text"))
        with patch("app.services.claude_service._get_client", return_value=mock_client):
            await generate_anomaly_narrative(_make_result())

        call_kwargs = mock_client.messages.create.call_args.kwargs
        assert call_kwargs["system"] == ANOMALY_SYSTEM

    async def test_prompt_includes_service_name(self):
        from app.services.claude_service import generate_anomaly_narrative

        mock_client = _make_mock_client(_mock_anthropic_response("narrative text"))
        with patch("app.services.claude_service._get_client", return_value=mock_client):
            await generate_anomaly_narrative(_make_result())

        call_kwargs = mock_client.messages.create.call_args.kwargs
        user_content = call_kwargs["messages"][0]["content"]
        assert "auth-service" in user_content

    async def test_prompt_includes_severity(self):
        from app.services.claude_service import generate_anomaly_narrative

        mock_client = _make_mock_client(_mock_anthropic_response("narrative text"))
        with patch("app.services.claude_service._get_client", return_value=mock_client):
            await generate_anomaly_narrative(_make_result(severity=Severity.CRITICAL))

        call_kwargs = mock_client.messages.create.call_args.kwargs
        user_content = call_kwargs["messages"][0]["content"]
        assert "CRITICAL" in user_content

    async def test_returns_text_from_response(self):
        from app.services.claude_service import generate_anomaly_narrative

        expected_narrative = "auth-service had 30 errors in 5 minutes."
        mock_client = _make_mock_client(_mock_anthropic_response(expected_narrative))
        with patch("app.services.claude_service._get_client", return_value=mock_client):
            result = await generate_anomaly_narrative(_make_result())

        assert result == expected_narrative

    async def test_returns_fallback_on_api_error(self):
        from app.services.claude_service import generate_anomaly_narrative

        mock_client = _make_failing_client(Exception("API error"))
        with patch("app.services.claude_service._get_client", return_value=mock_client):
            result = await generate_anomaly_narrative(_make_result())

        assert isinstance(result, str)
        assert len(result) > 0

    async def test_api_key_not_logged_on_error(self, caplog):
        import logging

        from app.services.claude_service import generate_anomaly_narrative

        mock_client = _make_failing_client(Exception("API error"))
        with patch("app.services.claude_service._get_client", return_value=mock_client):
            with caplog.at_level(logging.ERROR, logger="app.services.claude_service"):
                await generate_anomaly_narrative(_make_result())

        for record in caplog.records:
            full_text = f"{record.message} {record.exc_text or ''}"
            assert "sk-ant" not in full_text
            assert "api_key" not in full_text.lower()


# ---------------------------------------------------------------------------
# run_anomaly_check — narrative wired in
# ---------------------------------------------------------------------------


class TestRunAnomalyCheckWithNarrative:
    async def test_narrative_persisted_to_anomaly(self):
        """run_anomaly_check should call generate_anomaly_narrative and save it."""
        from app.services.anomaly_service import run_anomaly_check

        mock_db = AsyncMock()
        mock_db.refresh = AsyncMock()

        from datetime import datetime, timezone

        now = datetime.now(timezone.utc)
        fake_timestamps = [now - timedelta(seconds=i * 10) for i in range(30)]
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = fake_timestamps
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute = AsyncMock(return_value=mock_result)

        with patch(
            "app.services.anomaly_service.generate_anomaly_narrative",
            new_callable=AsyncMock,
        ) as mock_narrative:
            mock_narrative.return_value = "auth-service spike detected."
            anomaly = await run_anomaly_check(mock_db, "auth-service")

        assert anomaly is not None, "expected a detection with 30 error timestamps"
        added = mock_db.add.call_args[0][0]
        assert added.ai_narrative == "auth-service spike detected."
