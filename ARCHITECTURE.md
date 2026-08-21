# Architecture

High-level system architecture. Detailed specs live in [`docs/02_Architecture/`](docs/02_Architecture/).

## System Overview

```
                              Scheduler
                                 │
        ┌────────────────────────┼────────────────────────┐
        │                        │                        │
  Job Discovery Agent    Company Research Agent      JD Parser Agent
        │                        │                        │
        └────────────────────────┼────────────────────────┘
                                 │
                          Matching Agent
                                 │
                    Resume Optimization Agent
                                 │
                   Cover Letter Generator Agent
                                 │
                     ATS Validation Agent
                                 │
              Application Assistant Agent (human approval)
                                 │
                     Application Tracker
                                 │
                  Learning & Analytics Agent
                                 │
                        User Dashboard
```

## Components

| Component | Responsibility |
|---|---|
| Scheduler | Triggers periodic discovery/matching runs (Celery beat / cron) |
| Job Discovery Agent | Pulls postings from career pages, RSS, and public APIs |
| Company Research Agent | Enriches postings with company context |
| JD Parser Agent | Extracts structured skills/requirements from raw text |
| Matching Agent | Scores job–profile fit using embeddings + reranking |
| Resume Optimization Agent | Tailors resume content to a specific JD, truthfully |
| Cover Letter Generator Agent | Drafts a personalized cover letter |
| ATS Validation Agent | Checks formatting/keyword compliance |
| Application Assistant Agent | Fills forms via Playwright; **never submits without approval** |
| Application Tracker | Records status, history, and outcomes |
| Learning & Analytics Agent | Surfaces resume/skill/company performance trends |
| User Dashboard | Review, approve, and override every agent decision |

## Data Flow

1. Scheduler triggers Job Discovery on an interval.
2. Discovered postings are normalized and stored (PostgreSQL).
3. JD Parser + Company Research enrich each posting.
4. Matching Agent scores postings against the user's profile (pgvector similarity + reranker).
5. For postings above the match threshold: Resume Optimization → Cover Letter → ATS Validation.
6. A ready application is queued for **user approval** in the dashboard.
7. On approval, the Application Assistant submits via browser automation.
8. Outcomes (interview, rejection, no response) feed the Learning & Analytics Agent, which informs future resume/matching decisions.

## Cross-Cutting Concerns
- **Human-in-the-loop:** no application is submitted without explicit approval until the system has a proven, auditable track record.
- **No fabrication:** resume/cover-letter agents are constrained to the user's actual profile data; hallucination checks run before any document reaches the approval queue.
- **Observability:** every agent logs structured events (input, output, latency, cost) for debugging and analytics.
- **Isolation:** all user data (resumes, credentials, applications) is scoped per-user at the database and storage layer.

## Deployment Topology

```
Client (Dashboard) ── HTTPS ── API Gateway / NGINX ── FastAPI (backend)
                                                          │
                              ┌───────────────────────────┼───────────────────────────┐
                          PostgreSQL                    Redis                   Celery Workers (agents)
                          (+ pgvector)              (queue/cache)             (Playwright for automation)
```

Production runs on Kubernetes (see [`deployment/k8s/`](deployment/k8s/)); local development uses Docker Compose (see [`docker-compose.yml`](docker-compose.yml)).

## Related Documents
- [TECH_STACK.md](TECH_STACK.md) — technology choices and rationale
- [docs/02_Architecture/](docs/02_Architecture/) — database schema, API design, cloud architecture
- [docs/03_AI/](docs/03_AI/) — per-agent specifications
