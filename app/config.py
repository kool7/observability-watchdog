from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str
    anthropic_api_key: str
    webhook_url: str = "http://localhost:8000/webhook/receive"
    app_env: str = "development"
    version: str = "0.1.0"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
