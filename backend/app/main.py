"""
backend/app/main.py

FastAPI composition root.

Kept deliberately thin: it wires middleware, the root/health endpoints that
container orchestration depends on, and the versioned API routers. All business
logic lives in ``app/services`` and all HTTP shapes in ``app/schemas``.
"""

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.database import get_db

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    description="API for the autonomous job application pipeline",
    version="0.4.0",
)

# CORS: wildcard is fine for local development only. In production the
# CORS_ORIGINS env var must list explicit origins.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.api_v1_prefix)


@app.get("/", tags=["System"])
async def root() -> dict:
    """Service identity, useful for smoke tests and load balancers."""
    return {
        "service": settings.app_name,
        "version": app.version,
        "environment": settings.app_env,
        "docs": "/docs",
    }


@app.get("/health", tags=["System"])
async def health_check(db: AsyncSession = Depends(get_db)) -> dict:
    """
    Liveness and database connectivity probe.

    Always returns HTTP 200 so orchestrators can distinguish "process is up but
    the database is unreachable" (``database`` field) from "process is down".
    """
    try:
        await db.execute(text("SELECT 1"))
        db_status = "healthy"
    except Exception as exc:  # noqa: BLE001 - the point is to report, not crash
        db_status = f"unhealthy: {exc}"

    return {
        "status": "ok",
        "database": db_status,
        "environment": settings.app_env,
        "version": app.version,
    }


@app.post("/test-task", tags=["System"], include_in_schema=not settings.is_production)
async def trigger_dummy_task(message: str = "Hello Celery!") -> dict:
    """
    Dispatch a Celery smoke-test task.

    Hidden from the OpenAPI schema in production; it exists so operators can
    confirm the broker is wired up without running a worker-side command.
    """
    from app.tasks.dummy import dummy_task

    task = dummy_task.delay(message)
    return {"task_id": task.id, "status": "Task dispatched"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.app_debug,
    )
