from backend.app.core.config import get_settings


def test_settings_load():
    settings = get_settings()
    assert settings.app_env in {"development", "staging", "production"}
    assert settings.jwt_algorithm == "HS256"


def test_settings_cached():
    assert get_settings() is get_settings()
