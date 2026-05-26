import os

# Set defaults before any app module is imported so pydantic-settings
# picks up a valid asyncpg URL even when .env has a bare postgresql:// URL.
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/test")
os.environ.setdefault("ANTHROPIC_API_KEY", "sk-ant-test")

import pytest
from httpx import ASGITransport, AsyncClient


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
