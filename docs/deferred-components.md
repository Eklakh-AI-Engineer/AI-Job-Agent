| Component | Status | Intended Future Phase | Notes |
|-----------|--------|----------------------|-------|
| FastAPI | DEFERRED | Phase 3 (API Layer) | Existing code in `backend/app/main.py`. Provides `/health`, `/jobs` endpoints. |
| Next.js Dashboard | DEFERRED | Phase 4 (Frontend) | Existing code in `frontend/`. Glassmorphism dashboard with live job fetch. |
| PostgreSQL | DEFERRED | Phase 3+ (Production DB) | Currently configured via Docker Compose port 5434. |
| pgvector | DEFERRED | Phase 5 (Semantic Search) | Embedding column defined in existing `JobPosting` model. |
| Alembic | DEFERRED | Phase 3+ (Production Migrations) | Migration file at `backend/alembic/versions/`. |
| Redis | DEFERRED | Phase 3+ (Task Queue) | Configured as Celery broker in `docker-compose.yml`. |
| Celery | DEFERRED | Phase 3+ (Background Workers) | Configured in `backend/app/core/celery_app.py`. |
| Playwright | DEFERRED | Phase 3+ (Live Scraping) | Used in `backend/app/agents/discovery.py`. |
| Docker Compose | DEFERRED | Phase 3+ (Infrastructure) | Existing `docker-compose.yml` manages all services. |
