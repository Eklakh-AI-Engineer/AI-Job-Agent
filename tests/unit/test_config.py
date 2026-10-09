import os
from unittest.mock import patch

import pytest

from backend.app.core.config import Settings, get_settings


def test_settings_load():
    settings = get_settings()
    assert settings.app_env in {"development", "staging", "production"}
    assert settings.jwt_algorithm == "HS256"


def test_settings_cached():
    assert get_settings() is get_settings()


def test_validate_production_config_passes_with_proper_secrets():
    """Production config validation passes when all secrets are set."""
    with patch.dict(os.environ, {
        "APP_ENV": "production",
        "SECRET_KEY": "real-secret-key-32-chars-minimum",
        "JWT_SECRET": "real-jwt-secret-key-32-chars-minimum",
        "DATABASE_URL": "postgresql+asyncpg://user:realpass@localhost:5432/db",
        "CORS_ORIGINS": "https://app.example.com,https://api.example.com",
        "DOCUMENT_STORAGE_BACKEND": "supabase",
        "SUPABASE_URL": "https://example.supabase.co",
        "SUPABASE_SERVICE_ROLE_KEY": "service-role",
        "DOCUMENT_STORAGE_BUCKET": "artifacts",
    }):
        settings = Settings()
        settings.validate_production_config()  # Should not raise


def test_validate_production_config_fails_on_default_secret_key():
    """Production config validation fails when SECRET_KEY is default."""
    with patch.dict(os.environ, {
        "APP_ENV": "production",
        "SECRET_KEY": "change-me",
        "JWT_SECRET": "real-jwt-secret",
        "DATABASE_URL": "postgresql+asyncpg://user:realpass@localhost:5432/db",
        "CORS_ORIGINS": "https://app.example.com",
    }):
        settings = Settings()
        with pytest.raises(RuntimeError, match="SECRET_KEY must be set"):
            settings.validate_production_config()


def test_validate_production_config_fails_on_default_jwt_secret():
    """Production config validation fails when JWT_SECRET is default."""
    with patch.dict(os.environ, {
        "APP_ENV": "production",
        "SECRET_KEY": "real-secret-key",
        "JWT_SECRET": "change-me",
        "DATABASE_URL": "postgresql+asyncpg://user:realpass@localhost:5432/db",
        "CORS_ORIGINS": "https://app.example.com",
    }):
        settings = Settings()
        with pytest.raises(RuntimeError, match="JWT_SECRET must be set"):
            settings.validate_production_config()


def test_validate_production_config_fails_on_default_db_password():
    """Production config validation fails when DATABASE_URL contains default password."""
    with patch.dict(os.environ, {
        "APP_ENV": "production",
        "SECRET_KEY": "real-secret-key",
        "JWT_SECRET": "real-jwt-secret",
        "DATABASE_URL": "postgresql+asyncpg://user:change-me@localhost:5432/db",
        "CORS_ORIGINS": "https://app.example.com",
    }):
        settings = Settings()
        with pytest.raises(RuntimeError, match="DATABASE_URL must not contain default password"):
            settings.validate_production_config()


def test_validate_production_config_fails_on_wildcard_cors():
    """Production config validation fails when CORS_ORIGINS is wildcard."""
    with patch.dict(os.environ, {
        "APP_ENV": "production",
        "SECRET_KEY": "real-secret-key",
        "JWT_SECRET": "real-jwt-secret",
        "DATABASE_URL": "postgresql+asyncpg://user:realpass@localhost:5432/db",
        "CORS_ORIGINS": "*",
    }):
        settings = Settings()
        with pytest.raises(RuntimeError, match="CORS_ORIGINS must be explicitly set"):
            settings.validate_production_config()


def test_validate_production_config_skipped_in_development():
    """Production config validation is skipped in development mode."""
    with patch.dict(os.environ, {
        "APP_ENV": "development",
        "SECRET_KEY": "change-me",
        "JWT_SECRET": "change-me",
        "DATABASE_URL": "postgresql+asyncpg://user:change-me@localhost:5432/db",
        "CORS_ORIGINS": "*",
    }):
        settings = Settings()
        settings.validate_production_config()  # Should not raise in development


def test_supabase_postgres_url_is_normalized_for_asyncpg():
    settings = Settings(
        app_env="production",
        database_url="postgresql://postgres.project:pass@aws-0-region.pooler.supabase.com:6543/postgres?sslmode=require",
        secret_key="real-secret",
        jwt_secret="real-jwt-secret",
        cors_origins="https://app.example.com",
    )
    assert settings.effective_database_url.startswith("postgresql+asyncpg://")
    assert "ssl=require" in settings.effective_database_url
    assert "sslmode=" not in settings.effective_database_url

def test_production_managed_database_url_is_preserved():
    settings = Settings(
        app_env="production",
        database_url="postgresql+asyncpg://user:realpass@db.supabase.co:5432/postgres",
        secret_key="real-secret",
        jwt_secret="real-jwt-secret",
        cors_origins="https://app.example.com",
    )
    assert settings.effective_database_url == settings.database_url


def test_kubernetes_can_explicitly_use_internal_database():
    settings = Settings(
        app_env="production",
        use_in_cluster_database=True,
        database_url="postgresql+asyncpg://user:realpass@external.example:5432/db",
        database_host_in_cluster="postgres",
        database_port_in_cluster=5432,
        secret_key="real-secret",
        jwt_secret="real-jwt-secret",
        cors_origins="https://app.example.com",
    )
    assert "@postgres:5432/" in settings.effective_database_url


def test_supabase_transaction_pooler_disables_prepared_statement_cache():
    settings = Settings(
        app_env="production",
        database_url=(
            "postgresql://postgres.project:pass@aws-0-region.pooler.supabase.com:6543/"
            "postgres?sslmode=require&prepared_statement_cache_size=100"
        ),
        secret_key="real-secret",
        jwt_secret="real-jwt-secret",
        cors_origins="https://app.example.com",
    )
    url = settings.effective_database_url
    assert "prepared_statement_cache_size=0" in url
    assert "prepared_statement_cache_size=100" not in url
    assert "ssl=require" in url
