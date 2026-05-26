from contextlib import asynccontextmanager

from fastapi import FastAPI
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.config import settings
from app.middleware.rate_limiter import limiter
from app.routers.health import router as health_router
from app.routers.logs import router as logs_router


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

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.include_router(health_router)
app.include_router(logs_router)
