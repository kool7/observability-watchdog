from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import settings
from app.routers.health import router as health_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    from sqlalchemy import text

    from app.database import engine

    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception:
        pass  # allow startup without a live DB in unit-test environments
    yield
    await engine.dispose()


app = FastAPI(
    title="Observability Watchdog",
    version=settings.version,
    lifespan=lifespan,
)

app.include_router(health_router)
