"""Tests for global exception handlers and custom domain errors."""

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.middleware.error_handler import (
    ConflictError,
    NotFoundError,
    ServiceUnavailableError,
    WatchdogError,
    unhandled_error_handler,
    watchdog_error_handler,
)

# ---------------------------------------------------------------------------
# Domain exception attributes
# ---------------------------------------------------------------------------


class TestDomainExceptions:
    def test_not_found_has_correct_status(self):
        err = NotFoundError("resource missing")
        assert err.status_code == 404
        assert err.title == "Not Found"
        assert err.detail == "resource missing"

    def test_conflict_has_correct_status(self):
        err = ConflictError("duplicate key")
        assert err.status_code == 409
        assert err.title == "Conflict"

    def test_service_unavailable_has_correct_status(self):
        err = ServiceUnavailableError("downstream down")
        assert err.status_code == 503

    def test_instance_defaults_to_empty(self):
        err = WatchdogError("oops")
        assert err.instance == ""

    def test_instance_can_be_set(self):
        err = NotFoundError("gone", instance="/logs/abc")
        assert err.instance == "/logs/abc"


# ---------------------------------------------------------------------------
# Handler integration via FastAPI test app
# ---------------------------------------------------------------------------


@pytest.fixture
def error_app():
    app = FastAPI()
    app.add_exception_handler(WatchdogError, watchdog_error_handler)  # type: ignore[arg-type]
    app.add_exception_handler(Exception, unhandled_error_handler)  # type: ignore[arg-type]

    @app.get("/not-found")
    async def raise_not_found():
        raise NotFoundError("log entry not found", instance="/logs/missing-id")

    @app.get("/conflict")
    async def raise_conflict():
        raise ConflictError("entry already exists")

    @app.get("/crash")
    async def raise_unhandled():
        raise RuntimeError("unexpected boom")

    return app


class TestErrorHandlers:
    async def test_not_found_returns_404_problem_detail(self, error_app):
        async with AsyncClient(
            transport=ASGITransport(app=error_app), base_url="http://test"
        ) as client:
            resp = await client.get("/not-found")

        assert resp.status_code == 404
        body = resp.json()
        assert body["status"] == 404
        assert body["title"] == "Not Found"
        assert "log entry not found" in body["detail"]
        assert "type" in body
        assert "instance" in body

    async def test_conflict_returns_409(self, error_app):
        async with AsyncClient(
            transport=ASGITransport(app=error_app), base_url="http://test"
        ) as client:
            resp = await client.get("/conflict")

        assert resp.status_code == 409
        assert resp.json()["title"] == "Conflict"

    async def test_unhandled_returns_500_problem_detail(self):
        from starlette.requests import Request

        scope = {
            "type": "http",
            "method": "GET",
            "path": "/crash",
            "query_string": b"",
            "headers": [],
        }
        request = Request(scope)
        response = await unhandled_error_handler(
            request, RuntimeError("unexpected boom")
        )

        assert response.status_code == 500
        import json

        body = json.loads(response.body)
        assert body["status"] == 500
        assert body["title"] == "Internal Server Error"

    async def test_problem_detail_content_type(self, error_app):
        async with AsyncClient(
            transport=ASGITransport(app=error_app), base_url="http://test"
        ) as client:
            resp = await client.get("/not-found")

        assert "application/problem+json" in resp.headers["content-type"]

    async def test_problem_detail_has_type_url(self, error_app):
        async with AsyncClient(
            transport=ASGITransport(app=error_app), base_url="http://test"
        ) as client:
            resp = await client.get("/not-found")

        assert resp.json()["type"].startswith("https://httpstatuses.io/")
