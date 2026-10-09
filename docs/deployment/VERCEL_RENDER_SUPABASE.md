# Vercel + Supabase Deployment

## Target v1 topology

```text
GitHub
  |
  +--> Vercel (Next.js frontend)
  |          |
  |          +--> Vercel (FastAPI backend)
  |                    |
  |                    +--> Supabase PostgreSQL + pgvector
  |                    +--> Supabase Storage
  |
  +--> GitHub Actions CI / regression gates
```

This is the portfolio/free-tier production profile. Redis/Celery remain in the
repository for the full local/worker deployment profile, but they are not a
mandatory production dependency for the Vercel API paths used by the v1 UI.

## Vercel frontend

The existing `frontend/` application is deployed as the `ai-job-agent` Vercel
project. The verified production alias is:

`https://ai-job-agent-theta.vercel.app`

Set the frontend build variable to the verified backend alias:

`NEXT_PUBLIC_API_URL=https://ai-job-agent-api-mu.vercel.app`

Do not put database credentials, Supabase service-role keys, or other private
secrets in `NEXT_PUBLIC_*` variables.

## Vercel FastAPI backend

Create a second Vercel project from the same GitHub repository:

- Project name: `ai-job-agent-api`
- Root Directory: `backend`
- Framework: FastAPI
- Production branch: `main`

`backend/main.py` is the Vercel entrypoint and imports the canonical
`app.main:app`. The backend uses the existing `backend/requirements.txt`.

Required production environment variables:

- `APP_ENV=production`
- `APP_DEBUG=false`
- `USE_IN_CLUSTER_DATABASE=false`
- `DATABASE_URL`: Supabase PostgreSQL connection string
- `SECRET_KEY`: strong random secret
- `JWT_SECRET`: strong random secret
- `CORS_ORIGINS`: exact frontend origin, for example
  `https://ai-job-agent-theta.vercel.app`
- `OPENAI_API_KEY`: server-side only
- `DOCUMENT_STORAGE_BACKEND=supabase`
- `SUPABASE_URL`: the Supabase project URL
- `SUPABASE_SERVICE_ROLE_KEY`: server-side only
- `DOCUMENT_STORAGE_BUCKET`: private storage bucket name
- optional `DOCUMENT_STORAGE_PREFIX=documents`

Redis/Celery variables are not required for the synchronous v1 API surface.
The legacy `/test-task` endpoint is intentionally hidden from the production
OpenAPI schema and should not be used as a production health check.

## Supabase

Use the Supabase project as the system of record for:

- PostgreSQL
- pgvector
- private document/artifact storage

Run the repository's Alembic migrations against the Supabase database before
the first production smoke test. The Vercel runtime does not use the Docker
entrypoint, so migrations are not implicitly applied on function startup.

Create a private Storage bucket matching `DOCUMENT_STORAGE_BUCKET`. The backend
now includes a native Supabase Storage HTTP adapter, so no separate Redis or
object-storage service is required.

## Health and live QA

Backend health endpoint:

`https://ai-job-agent-api-mu.vercel.app/health`

Frontend live QA:

`LIVE_API_URL=https://ai-job-agent-api-mu.vercel.app npm run test:live`

`FRONTEND_URL=https://ai-job-agent-theta.vercel.app npm run test:live:frontend`

Production smoke tests must verify `/health`, authentication, database access,
job listing, document artifact persistence, and the frontend-to-API path.

## Full worker profile

Local/Docker/Kubernetes deployments may continue to use Redis + Celery +
Playwright for scheduled discovery and long-running browser automation. That
profile is deliberately separate from the free Vercel/Supabase v1 deployment.
