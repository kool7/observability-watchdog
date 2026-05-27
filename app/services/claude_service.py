from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from anthropic import AsyncAnthropic
from anthropic.types import TextBlock

from app.config import settings
from app.prompts import ANOMALY_SYSTEM, ANOMALY_USER

if TYPE_CHECKING:
    from app.services.anomaly_detector import AnomalyResult

logger = logging.getLogger(__name__)

_client: AsyncAnthropic | None = None


def _get_client() -> AsyncAnthropic:
    global _client
    if _client is None:
        _client = AsyncAnthropic(api_key=settings.anthropic_api_key)
    return _client


def _build_user_prompt(result: AnomalyResult) -> str:
    return ANOMALY_USER.format(
        service_name=result.service_name,
        severity=result.severity.value,
        z_score=result.z_score,
        threshold=result.threshold_breached,
        error_count=result.error_count,
        window_start=result.window_start.isoformat(),
        window_end=result.window_end.isoformat(),
    )


async def generate_anomaly_narrative(result: AnomalyResult) -> str:
    """Call Claude to generate a 2-3 sentence incident narrative for an anomaly."""
    try:
        message = await _get_client().messages.create(
            model=settings.claude_model,
            max_tokens=settings.claude_max_tokens,
            system=ANOMALY_SYSTEM,
            messages=[{"role": "user", "content": _build_user_prompt(result)}],
        )
        block = message.content[0]
        if isinstance(block, TextBlock):
            return block.text
        return str(block)
    except Exception:
        logger.exception(
            "Failed to generate narrative for service %s severity %s",
            result.service_name,
            result.severity.value,
        )
        return (
            f"{result.service_name} reported a {result.severity.value} severity "
            f"anomaly with {result.error_count} errors (Z={result.z_score:.2f})."
        )
