def test_settings_loads():
    from app.config import settings

    assert settings.app_env in ("development", "test")
    assert settings.webhook_url.startswith("http")
    assert bool(settings.database_url)
    assert bool(settings.anthropic_api_key)
    assert settings.database_url.startswith("postgresql+asyncpg://")


def test_database_url_normalised_from_postgres():
    from app.config import Settings

    s = Settings(
        database_url="postgres://user:pass@host/db",
        anthropic_api_key="sk-ant-test",
    )
    assert s.database_url == "postgresql+asyncpg://user:pass@host/db"


def test_database_url_normalised_from_postgresql():
    from app.config import Settings

    s = Settings(
        database_url="postgresql://user:pass@host/db",
        anthropic_api_key="sk-ant-test",
    )
    assert s.database_url == "postgresql+asyncpg://user:pass@host/db"


def test_database_url_unchanged_when_already_asyncpg():
    from app.config import Settings

    url = "postgresql+asyncpg://user:pass@host/db"
    s = Settings(database_url=url, anthropic_api_key="sk-ant-test")
    assert s.database_url == url
