# AI Job Agent Development

## Prerequisites

The repository is designed around:

- Python;
- Docker / Docker Compose;
- PostgreSQL with pgvector;
- Redis.

Check `.env.example` for configuration names before starting local services.

## Local setup

```bash
git clone https://github.com/Eklakh-AI-Engineer/AI-Job-Agent.git
cd AI-Job-Agent
cp .env.example .env
```

Start the stack:

```bash
docker compose up -d --build
```

The API exposes interactive FastAPI documentation at `/docs` when running.

## Testing

Default fast suite:

```bash
pytest
```

PostgreSQL integration suite:

```bash
pytest -m postgres tests/integration_pg
```

The repository's recorded baseline is 188 fast tests and 13 PostgreSQL integration tests. Treat these as historical verification until CI or a local run confirms the current state.

## Migrations

Alembic migrations are part of the backend persistence workflow. Use the repository's existing migration configuration rather than creating parallel schema-management paths.

## Development principles

1. Keep API routers thin.
2. Put business behavior in services/domain modules.
3. Keep persistence concerns explicit.
4. Add migrations with corresponding test coverage.
5. Keep external automation behind human-approval boundaries.
6. Do not hard-code secrets.
7. Update active documentation when implementation status changes.
8. Do not present roadmap components as implemented features.
