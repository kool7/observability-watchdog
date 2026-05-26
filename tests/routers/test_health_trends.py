"""Tests for GET /health/trends — 5-minute bucket time-series."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.schemas.trends import TrendBucketResponse


def _make_bucket(
    service_name="auth-service", error_count=5, warn_count=2, info_count=10
):
    return TrendBucketResponse(
        bucket=datetime.now(timezone.utc).replace(second=0, microsecond=0),
        service_name=service_name,
        error_count=error_count,
        warn_count=warn_count,
        info_count=info_count,
    )


# ---------------------------------------------------------------------------
# GET /health/trends
# ---------------------------------------------------------------------------


class TestHealthTrends:
    async def test_returns_200(self):
        with patch(
            "app.routers.health.get_log_trends", new_callable=AsyncMock
        ) as mock_trends:
            mock_trends.return_value = []
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.get("/health/trends")

        assert resp.status_code == 200

    async def test_returns_list(self):
        with patch(
            "app.routers.health.get_log_trends", new_callable=AsyncMock
        ) as mock_trends:
            mock_trends.return_value = [_make_bucket()]
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.get("/health/trends")

        assert isinstance(resp.json(), list)
        assert len(resp.json()) == 1

    async def test_bucket_has_required_fields(self):
        with patch(
            "app.routers.health.get_log_trends", new_callable=AsyncMock
        ) as mock_trends:
            mock_trends.return_value = [
                _make_bucket(error_count=10, warn_count=3, info_count=20)
            ]
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.get("/health/trends")

        item = resp.json()[0]
        assert "bucket" in item
        assert "service_name" in item
        assert "error_count" in item
        assert "warn_count" in item
        assert "info_count" in item
        assert item["error_count"] == 10
        assert item["warn_count"] == 3
        assert item["info_count"] == 20

    async def test_default_hours_is_6(self):
        with patch(
            "app.routers.health.get_log_trends", new_callable=AsyncMock
        ) as mock_trends:
            mock_trends.return_value = []
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                await client.get("/health/trends")

        call_kwargs = mock_trends.call_args.kwargs
        assert call_kwargs["hours"] == 6

    async def test_custom_hours_forwarded(self):
        with patch(
            "app.routers.health.get_log_trends", new_callable=AsyncMock
        ) as mock_trends:
            mock_trends.return_value = []
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                await client.get("/health/trends?hours=24")

        call_kwargs = mock_trends.call_args.kwargs
        assert call_kwargs["hours"] == 24

    async def test_service_name_filter_forwarded(self):
        with patch(
            "app.routers.health.get_log_trends", new_callable=AsyncMock
        ) as mock_trends:
            mock_trends.return_value = []
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                await client.get("/health/trends?service_name=auth-service")

        call_kwargs = mock_trends.call_args.kwargs
        assert call_kwargs["service_name"] == "auth-service"

    async def test_no_filter_passes_none(self):
        with patch(
            "app.routers.health.get_log_trends", new_callable=AsyncMock
        ) as mock_trends:
            mock_trends.return_value = []
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                await client.get("/health/trends")

        call_kwargs = mock_trends.call_args.kwargs
        assert call_kwargs["service_name"] is None

    async def test_empty_when_no_logs(self):
        with patch(
            "app.routers.health.get_log_trends", new_callable=AsyncMock
        ) as mock_trends:
            mock_trends.return_value = []
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.get("/health/trends")

        assert resp.json() == []

    @pytest.mark.parametrize(
        "url",
        [
            "/health/trends?hours=0",
            "/health/trends?hours=-1",
            "/health/trends?hours=169",
            "/health/trends?service_name=",
        ],
    )
    async def test_invalid_params_return_422(self, url):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get(url)

        assert resp.status_code == 422
