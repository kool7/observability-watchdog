from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from anthropic import AsyncAnthropic
from anthropic.types import TextBlock

from app.config import settings

if TYPE_CHECKING:
    from app.services.anomaly_detector import AnomalyResult

logger = logging.getLogger(__name__)

_client: AsyncAnthropic | None = None


def _get_client() -> AsyncAnthropic:
    global _client
    if _client is None:
        _client = AsyncAnthropic()
    return _client


def _build_prompt(result: AnomalyResult) -> str:
    window = f"{result.window_start.isoformat()} to {result.window_end.isoformat()}"
    return (
        f"An anomaly was detected in service '{result.service_name}'.\n"
        f"Severity: {result.severity.value}\n"
        f"Z-score: {result.z_score:.2f} (threshold: {result.threshold_breached})\n"
        f"Error count in window: {result.error_count}\n"
        f"Window: {window}\n\n"
        "Write a concise 2-3 sentence incident narrative suitable for an "
        "on-call engineer. Be specific about the service, severity, and error "
        "spike. Do not suggest fixes."
    )


async def generate_anomaly_narrative(result: AnomalyResult) -> str:
    """Call Claude to generate a 2-3 sentence incident narrative for an anomaly."""
    try:
        message = await _get_client().messages.create(
            model=settings.claude_model,
            max_tokens=settings.claude_max_tokens,
            messages=[{"role": "user", "content": _build_prompt(result)}],
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
