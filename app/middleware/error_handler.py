"""
Global exception handling with RFC 7807 Problem Details responses.

All unhandled domain errors and unexpected exceptions return a consistent
JSON structure so API consumers can parse errors reliably.
"""

from __future__ import annotations

import logging

from fastapi import Request
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Custom domain exceptions
# ---------------------------------------------------------------------------


class WatchdogError(Exception):
    """Base class for all domain errors raised within Observability Watchdog."""

    status_code: int = 500
    title: str = "Internal Server Error"

    def __init__(self, detail: str, instance: str = "") -> None:
        super().__init__(detail)
        self.detail = detail
        self.instance = instance


class NotFoundError(WatchdogError):
    status_code = 404
    title = "Not Found"


class ConflictError(WatchdogError):
    status_code = 409
    title = "Conflict"


class ServiceUnavailableError(WatchdogError):
    status_code = 503
    title = "Service Unavailable"


# ---------------------------------------------------------------------------
# Problem Details builder (RFC 7807)
# ---------------------------------------------------------------------------


def _problem_detail(
    status: int, title: str, detail: str, instance: str
) -> dict[str, object]:
    return {
        "type": f"https://httpstatuses.io/{status}",
        "title": title,
        "status": status,
        "detail": detail,
        "instance": instance,
    }


# ---------------------------------------------------------------------------
# Exception handlers
# ---------------------------------------------------------------------------


async def watchdog_error_handler(request: Request, exc: WatchdogError) -> JSONResponse:
    body = _problem_detail(
        exc.status_code,
        exc.title,
        exc.detail,
        exc.instance or str(request.url),
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=body,
        media_type="application/problem+json",
    )


async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled error on %s %s", request.method, request.url)
    body = _problem_detail(
        500,
        "Internal Server Error",
        "An unexpected error occurred. Please try again later.",
        str(request.url),
    )
    return JSONResponse(
        status_code=500,
        content=body,
        media_type="application/problem+json",
    )
