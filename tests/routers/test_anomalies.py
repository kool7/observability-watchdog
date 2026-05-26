"""Tests for the anomalies router — GET /anomalies and GET /anomalies/{id}."""

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.middleware.error_handler import NotFoundError
from tests.__fixtures__.anomalies import make_anomaly


class TestListAnomalies:
    async def test_returns_list_of_anomalies(self):
        with patch(
            "app.routers.anomalies.list_anomalies", new_callable=AsyncMock
        ) as mock_list:
            mock_list.return_value = [make_anomaly()]

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.get("/anomalies")

        assert resp.status_code == 200
        body = resp.json()
        assert isinstance(body, list)
        assert len(body) == 1

    async def test_returns_empty_list_when_no_anomalies(self):
        with patch(
            "app.routers.anomalies.list_anomalies", new_callable=AsyncMock
        ) as mock_list:
            mock_list.return_value = []

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.get("/anomalies")

        assert resp.status_code == 200
        assert resp.json() == []

    async def test_anomaly_has_required_fields(self):
        with patch(
            "app.routers.anomalies.list_anomalies", new_callable=AsyncMock
        ) as mock_list:
            mock_list.return_value = [make_anomaly()]

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.get("/anomalies")

        item = resp.json()[0]
        for field in (
            "id",
            "service_name",
            "detected_at",
            "severity",
            "error_count",
            "z_score",
            "webhook_fired",
        ):
            assert field in item

    @pytest.mark.parametrize(
        "url",
        [
            "/anomalies?limit=0",
            "/anomalies?limit=-1",
            "/anomalies?limit=201",
        ],
    )
    async def test_invalid_limit_returns_422(self, url):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get(url)
        assert resp.status_code == 422


class TestGetAnomalyById:
    async def test_returns_anomaly_for_valid_id(self):
        anomaly = make_anomaly()
        with patch(
            "app.routers.anomalies.get_anomaly", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = anomaly

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.get(f"/anomalies/{anomaly.id}")

        assert resp.status_code == 200
        assert resp.json()["id"] == str(anomaly.id)

    async def test_returns_404_when_anomaly_not_found(self):
        missing_id = uuid.uuid4()
        with patch(
            "app.routers.anomalies.get_anomaly", new_callable=AsyncMock
        ) as mock_get:
            mock_get.side_effect = NotFoundError(f"Anomaly {missing_id} not found")

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.get(f"/anomalies/{missing_id}")

        assert resp.status_code == 404

    async def test_returns_422_for_non_uuid_id(self):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/anomalies/not-a-uuid")

        assert resp.status_code == 422
