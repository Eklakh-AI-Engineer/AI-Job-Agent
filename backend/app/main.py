from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.core.config import get_settings
from app.core.database import get_db

settings = get_settings()

app = FastAPI(
    title="AI Job Agent API",
    description="API for the autonomous job application pipeline",
    version="0.1.0",
)

# CORS setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict this in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health", tags=["System"])
async def health_check(db: AsyncSession = Depends(get_db)):
    """
    Health check endpoint to verify API and Database connectivity.
    """
    try:
        # Check database connectivity
        await db.execute(text("SELECT 1"))
        db_status = "healthy"
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"
        
    return {
        "status": "ok",
        "database": db_status,
        "environment": settings.app_env,
        "version": app.version
    }

@app.post("/test-task", tags=["System"])
async def trigger_dummy_task(message: str = "Hello Celery!"):
    from app.tasks.dummy import dummy_task
    task = dummy_task.delay(message)
    return {"task_id": task.id, "status": "Task dispatched"}

@app.get("/jobs", tags=["Jobs"])
async def get_jobs(db: AsyncSession = Depends(get_db)):
    from sqlalchemy.future import select
    from app.models.job import JobPosting
    result = await db.execute(select(JobPosting).order_by(JobPosting.id.desc()).limit(100))
    jobs = result.scalars().all()
    return jobs

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=settings.app_debug)
