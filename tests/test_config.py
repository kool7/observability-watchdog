def test_settings_loads():
    from app.config import settings

    assert settings.app_env in ("development", "test")
    assert settings.webhook_url == "http://localhost:8000/webhook/receive"
    assert settings.database_url is not None
    assert settings.anthropic_api_key is not None
