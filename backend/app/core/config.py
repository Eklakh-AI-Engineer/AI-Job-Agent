from functools import lru_cache
from typing import List
from urllib.parse import urlparse, urlunparse

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
        """
        Return the database URL appropriate for the current environment.
        
        Use the configured DATABASE_URL by default, including managed
        PostgreSQL such as Supabase. Kubernetes deployments may explicitly set
        USE_IN_CLUSTER_DATABASE=true to use the internal postgres service.
        """
        if self.is_production and self.use_in_cluster_database:
            parsed = urlparse(self.database_url)
            # Replace host and port with in-cluster values
            netloc = f"{parsed.username}:{parsed.password}@{self.database_host_in_cluster}:{self.database_port_in_cluster}"
            return urlunparse((
                parsed.scheme,
                netloc,
                parsed.path,
                parsed.params,
                parsed.query,
                parsed.fragment,
            ))
        return self.database_url

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

        if errors:
            raise RuntimeError("Production configuration invalid:\n  - " + "\n  - ".join(errors))


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.validate_production_config()
    return settings
