# AI Job Agent Development

## Prerequisites

- Python
- Docker / Docker Compose
- PostgreSQL with pgvector
- Redis
- Node.js / npm for the frontend

## Local setup

```bash
git clone https://github.com/Eklakh-AI-Engineer/AI-Job-Agent.git
cd AI-Job-Agent
cp .env.example .env
docker compose up -d --build
```

## Backend testing

```bash
pytest
pytest -m postgres tests/integration_pg
```

Previously recorded development evidence was 233 backend tests. Treat counts as historical until local or CI execution confirms the current state.

## Frontend testing

```bash
cd frontend
npm install
npm test
npm run lint
npm run build
```

The frontend is already part of the repository. Backend work should not trigger a frontend rebuild unless an integration contract changes.

## Migrations

```bash
cd backend
alembic upgrade head
```

Use the existing Alembic path; do not create parallel schema-management paths.

## Engineering status rules

- **Implemented**: source exists.
- **Integrated**: connected to an application path.
- **Validated**: tests or controlled execution provide evidence.
- **Planned**: work remains.

A source file, endpoint or UI component alone is not evidence of end-to-end functionality.

## Development principles

1. Keep routers thin.
2. Put business behavior in services/domain modules.
3. Keep persistence boundaries explicit.
4. Add migrations with corresponding tests.
5. Keep external automation behind human approval.
6. Do not hard-code secrets.
7. Preserve source and candidate evidence.
8. Update active documentation when implementation status changes.
9. Do not present roadmap components as implemented.
10. Record measurable validation evidence for important changes.

## Current engineering priority

Repository correctness -> real JD extraction -> canonical JobPosting -> candidate/job ranking -> golden evaluation -> professional documents -> controlled ATS E2E -> full product E2E -> CI release gate.

See [PENDING_IMPLEMENTATION_PLAN.md](../PENDING_IMPLEMENTATION_PLAN.md).