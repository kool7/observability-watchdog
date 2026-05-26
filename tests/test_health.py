from httpx import AsyncClient


async def test_health_returns_ok(client: AsyncClient):
    response = await client.get("/health")
    assert response.status_code == 200


async def test_health_response_body(client: AsyncClient):
    response = await client.get("/health")
    data = response.json()
    assert data["status"] == "ok"
    assert "version" in data


async def test_health_content_type(client: AsyncClient):
    response = await client.get("/health")
    assert "application/json" in response.headers["content-type"]
