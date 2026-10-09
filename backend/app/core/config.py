from functools import lru_cache
from typing import List
import os
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_env: str = "development"
    app_debug: bool = True
    app_name: str = "AI Job Agent API"
    database_url: str = (
        "postgresql+asyncpg://aijobagent:change-me@127.0.0.1:5434/aijobagent"
    )
    # In-cluster database host (Kubernetes service name)
    database_host_in_cluster: str = "postgres"
    database_port_in_cluster: int = 5432
    use_in_cluster_database: bool = False
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"
    playwright_headless: bool = True

    # ---- Auth ----
    secret_key: str = "change-me"
    jwt_secret: str = "change-me"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60

    # ---- HTTP ----
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_v1_prefix: str = "/api/v1"
    cors_origins: str = "*"

    model_config = {"env_file": "../.env", "extra": "ignore"}

    @property
    def cors_origin_list(self) -> List[str]:
        """Parse the comma-separated CORS origin setting into a list."""
        return [
            origin.strip() for origin in self.cors_origins.split(",") if origin.strip()
        ]

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def effective_database_url(self) -> str:
        """Return an asyncpg-compatible database URL.

        Supabase commonly exposes postgresql:// URLs while this service
        uses SQLAlchemy's asyncpg driver. Normalize postgres:// and
        postgresql:// to postgresql+asyncpg:// and translate sslmode to ssl.
        """
        database_url = self.database_url

        if self.is_production and self.use_in_cluster_database:
            parsed = urlparse(database_url)
            netloc = (
                f"{parsed.username}:{parsed.password}@"
                f"{self.database_host_in_cluster}:{self.database_port_in_cluster}"
            )
            database_url = urlunparse((
                parsed.scheme,
                netloc,
                parsed.path,
                parsed.params,
                parsed.query,
                parsed.fragment,
            ))

        parsed = urlparse(database_url)
        scheme = parsed.scheme
        if scheme in {"postgres", "postgresql"}:
            scheme = "postgresql+asyncpg"

        query = parse_qsl(parsed.query, keep_blank_values=True)
        query = [
            ("ssl" if key == "sslmode" else key, value)
            for key, value in query
        ]

        # Supabase transaction-mode PgBouncer can reuse server connections
        # across clients. Disable SQLAlchemy's asyncpg prepared-statement cache
        # as well as asyncpg's own statement cache (configured in database.py).
        # Without both settings, concurrent health checks can intermittently fail
        # with DuplicatePreparedStatementError even when the database is healthy.
        if parsed.port == 6543:
            query = [
                (key, value)
                for key, value in query
                if key != "prepared_statement_cache_size"
            ]
            query.append(("prepared_statement_cache_size", "0"))

        return urlunparse((
            scheme,
            parsed.netloc,
            parsed.path,
            parsed.params,
            urlencode(query),
            parsed.fragment,
        ))

    def validate_production_config(self) -> None:
        """Validate that production-critical secrets are not using defaults.
        
        Raises:
            RuntimeError: If any production secret is still using its default value.
        """
        if not self.is_production:
            return

        errors: List[str] = []

        if self.secret_key == "change-me":
            errors.append("SECRET_KEY must be set (not 'change-me') in production")
        if self.jwt_secret == "change-me":
            errors.append("JWT_SECRET must be set (not 'change-me') in production")
        if "change-me" in self.database_url:
            errors.append("DATABASE_URL must not contain default password 'change-me' in production")
        if self.cors_origins == "*":
            errors.append("CORS_ORIGINS must be explicitly set (not '*') in production")

        storage_backend = os.getenv("DOCUMENT_STORAGE_BACKEND", "local").lower()
        if storage_backend == "local":
            errors.append("DOCUMENT_STORAGE_BACKEND must be 'supabase' or 's3' in production")
        if storage_backend == "supabase":
            if not os.getenv("SUPABASE_URL"):
                errors.append("SUPABASE_URL must be set when DOCUMENT_STORAGE_BACKEND='supabase'")
            if not os.getenv("SUPABASE_SERVICE_ROLE_KEY"):
                errors.append("SUPABASE_SERVICE_ROLE_KEY must be set when DOCUMENT_STORAGE_BACKEND='supabase'")
            if not os.getenv("DOCUMENT_STORAGE_BUCKET"):
                errors.append("DOCUMENT_STORAGE_BUCKET must be set when DOCUMENT_STORAGE_BACKEND='supabase'")

        if errors:
            raise RuntimeError("Production configuration invalid:\n  - " + "\n  - ".join(errors))


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.validate_production_config()
    return settings
