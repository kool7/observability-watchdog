import os

# Set defaults before any app module is imported so pydantic-settings
# picks up a valid asyncpg URL even when .env has a bare postgresql:// URL.
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/test")
os.environ.setdefault("ANTHROPIC_API_KEY", "sk-ant-test")

from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient


@pytest.fixture(autouse=True)
def mock_anomaly_check():
    """Suppress DB-hitting anomaly check in all ingest tests by default."""
    with patch("app.routers.logs.run_anomaly_check", new_callable=AsyncMock) as m:
        m.return_value = None
        yield m


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    """Clear slowapi in-memory storage between tests to prevent state bleed."""
    from app.middleware.rate_limiter import limiter

    storage = getattr(limiter, "_storage", None)
    if storage is not None:
        storage.reset()
    yield


@pytest.fixture
async def client():
    from app.main import app

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac
