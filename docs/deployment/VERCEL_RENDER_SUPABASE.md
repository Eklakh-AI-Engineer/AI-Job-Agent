# Deployment Configuration

## Target v1 topology

```text
Vercel (Next.js)
       |
       v
Render Web -> FastAPI
       |       |
       |       +--> Redis
       |
       +----------> Supabase PostgreSQL + pgvector
       |
       +----------> Supabase Storage via the S3-compatible storage adapter
       |
       +----------> Render Celery worker
```

## Render

`render.yaml` defines the API web service and Celery worker. The repository does
not provision a managed Redis or database in the Blueprint because the intended
v1 stack uses Supabase for PostgreSQL/pgvector and an externally managed Redis
endpoint.

Set these secrets/values in Render:

- `DATABASE_URL`: Supabase PostgreSQL connection string.
- `REDIS_URL`, `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND`: managed Redis URLs.
- `CORS_ORIGINS`: the exact Vercel origin, with no wildcard.
- `OPENAI_API_KEY`: server-side only.
- `S3_ENDPOINT_URL`, `S3_ACCESS_KEY`, `S3_SECRET_KEY`, `S3_BUCKET`: server-side
  storage configuration when using the S3-compatible storage adapter.

The API health endpoint is `/health`. The Docker entrypoint applies Alembic
migrations before starting the selected process.

## Vercel

The `frontend/` directory is a standard Next.js application. Configure:

`NEXT_PUBLIC_API_URL=https://<render-api-host>`

Do not put private keys or database credentials in `NEXT_PUBLIC_*` variables.

## Supabase

Use Supabase PostgreSQL as the managed database and enable pgvector. Keep
`USE_IN_CLUSTER_DATABASE=false` for this topology so the application uses the
managed `DATABASE_URL` directly.

For generated PDF/DOCX artifacts, the existing storage abstraction can use an
S3-compatible endpoint. Create a private bucket and keep server-side storage
credentials out of the frontend.

## Local vs production

- Local: Docker Compose PostgreSQL/Redis + local document storage.
- Production: Render API/worker + Supabase PostgreSQL/Storage + managed Redis +
  Vercel frontend.
- Kubernetes remains an alternative deployment target; set
  `USE_IN_CLUSTER_DATABASE=true` only when the database really is exposed as the
  configured in-cluster service.
