from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_env: str = "development"
    app_debug: bool = True
    database_url: str = "postgresql+asyncpg://aijobagent:change-me@127.0.0.1:5434/aijobagent"
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"
    playwright_headless: bool = True
    jwt_secret: str = "change-me"
    jwt_algorithm: str = "HS256"

    model_config = {"env_file": "../.env", "extra": "ignore"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
