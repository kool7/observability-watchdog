from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str
    anthropic_api_key: str
    webhook_url: str = "http://localhost:8000/webhook/receive"
    app_env: str = "development"
    version: str = "0.1.0"
    claude_model: str = "claude-sonnet-4-6"
    claude_max_tokens: int = 256

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @field_validator("database_url")
    @classmethod
    def ensure_asyncpg_driver(cls, v: str) -> str:
        # Normalise scheme for SQLAlchemy async
        if v.startswith("postgres://"):
            v = v.replace("postgres://", "postgresql+asyncpg://", 1)
        elif v.startswith("postgresql://"):
            v = v.replace("postgresql://", "postgresql+asyncpg://", 1)

        # asyncpg rejects psycopg2-style sslmode / channel_binding params.
        # Replace sslmode=require with ssl=require (asyncpg-native).
        parsed = urlparse(v)
        params = {k: vals[0] for k, vals in parse_qs(parsed.query).items()}
        ssl_mode = params.pop("sslmode", None)
        params.pop("channel_binding", None)
        if ssl_mode == "require":
            params["ssl"] = "require"
        clean_query = urlencode(params)
        return urlunparse(parsed._replace(query=clean_query))


settings = Settings()
