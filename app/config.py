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
        # Neon and most Postgres providers give postgresql:// or postgres://
        # SQLAlchemy async requires postgresql+asyncpg://
        if v.startswith("postgres://"):
            return v.replace("postgres://", "postgresql+asyncpg://", 1)
        if v.startswith("postgresql://"):
            return v.replace("postgresql://", "postgresql+asyncpg://", 1)
        return v


settings = Settings()
