def test_settings_loads():
    from app.config import settings

    assert settings.app_env in ("development", "test")
    assert settings.webhook_url.startswith("http")
    assert bool(settings.database_url)
    assert bool(settings.anthropic_api_key)
