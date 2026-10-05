# Development Guide

## Prerequisites
- Docker & Docker Compose
- Python 3.12+ (for running tools outside containers)
- Make

## Local Setup
```bash
git clone https://github.com/OWNER/AI-Job-Agent.git
cd AI-Job-Agent
cp .env.example .env       # fill in secrets/API keys
make setup                 # installs pre-commit hooks, builds images
make up                    # starts backend, postgres, redis via docker-compose
make migrate                # applies database migrations
```

The API is available at `http://localhost:8000` (docs at `/docs`).

## Common Commands
| Command | Description |
|---|---|
| `make up` | Start all services |
| `make down` | Stop all services |
| `make logs` | Tail logs for all services |
| `make test` | Run the full test suite |
| `make test-unit` | Unit tests only |
| `make test-integration` | Integration tests only |
| `make lint` | Run `ruff` + `black --check` |
| `make format` | Auto-format with `black` |
| `make migrate` | Apply DB migrations |
| `make migration name=...` | Generate a new migration |
| `make shell` | Open a shell in the backend container |

## Branching & Commits
Follow the conventions in [CONTRIBUTING.md](CONTRIBUTING.md): `feature/*` / `bugfix/*` branches, [Conventional Commits](https://www.conventionalcommits.org/) messages.

## Testing Strategy
- **Unit tests** (`tests/unit/`) — pure functions, agent prompt-building logic, parsers
- **Integration tests** (`tests/integration/`) — API endpoints against a real Postgres/Redis in Docker
- **End-to-end tests** (`tests/e2e/`) — full pipeline runs against mocked job sources and a sandboxed browser target

Run everything CI runs, locally:
```bash
make lint && make test
```

## Environment Variables
See [`.env.example`](.env.example) for the full list. Never commit a populated `.env` file.

## Adding a New Agent
1. Create `backend/app/agents/<agent_name>.py`.
2. Document it in `docs/03_AI/<Agent_Name>.md` (purpose, inputs, outputs, prompt, failure handling, cost/latency).
3. Add unit tests for its logic and an integration test for its API surface.
4. Register it with the scheduler/orchestrator.

## Debugging
- Structured logs are emitted as JSON; use `make logs` or your platform's log viewer.
- Local Grafana/Prometheus can be started via `docker compose -f monitoring/docker-compose.monitoring.yml up` (see [`monitoring/`](monitoring/)).

## Getting Help
See [SUPPORT.md](SUPPORT.md).
