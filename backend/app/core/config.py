from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_env: str = "development"
    app_debug: bool = True
    app_name: str = "AI Job Agent API"
    database_url: str = (
        "postgresql+asyncpg://aijobagent:change-me@127.0.0.1:5434/aijobagent"
    )
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


@lru_cache
def get_settings() -> Settings:
    return Settings()
