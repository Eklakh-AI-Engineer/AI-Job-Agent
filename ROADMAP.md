# Roadmap

This roadmap tracks AI Job Agent from repository foundation through a production-ready v1.0. Timelines are indicative and adjusted as work progresses.

## Guiding Principles
- Documentation and architecture precede implementation.
- No auto-apply without human approval until the system has a proven track record.
- Every phase ships something demonstrable, not just documents.

## Phase 1 — Foundation (Current)
**Goal:** A repository that looks and operates like a mature open-source / startup project.
- [x] Governance files: README, LICENSE, CONTRIBUTING, CODE_OF_CONDUCT, SECURITY, SUPPORT, CHANGELOG
- [x] ROADMAP, ARCHITECTURE, TECH_STACK, DEVELOPMENT_GUIDE
- [x] Tooling: `.env.example`, `Dockerfile`, `docker-compose.yml`, `.gitignore`, `.editorconfig`, `.gitattributes`, `Makefile`
- [x] CI/CD: GitHub Actions (lint, test, CodeQL, Docker publish)
- [x] Issue templates, PR template, CODEOWNERS
- [x] `docs/` skeleton, test scaffolding (unit/integration/e2e), monitoring & deployment config skeleton

## Phase 2 — Documentation & Research
**Goal:** Every subsequent engineering decision is grounded in a written document.
- Project vision, problem statement, objectives, scope, success metrics
- Market research, competitor analysis, user personas, business model, risk register
- System, agent, database, API, and cloud architecture specs
- Technology evaluation / ADRs

## Phase 3 — Backend Foundation (Current)
- [x] FastAPI service skeleton: versioned `/api/v1` routers, root and `/health` probes
- [x] PostgreSQL schema + Alembic migration (`users`, `job_postings`, `application_statuses`)
- [x] Redis + Celery wiring (broker, result backend, worker/beat containers)
- [x] Authentication: bcrypt password hashing, JWT bearer tokens, register/login/me
- [x] Service layer (`app/services`) and request/response schemas (`app/schemas`)
- [x] Dockerized local dev environment, CI running lint plus unit and integration tests
- [x] Integration tests against real PostgreSQL + pgvector (`tests/integration_pg/`)
- [x] In-container alembic upgrade on boot (entrypoint script)
- [x] `backend.*` import-path compatibility (relative imports + PYTHONPATH=/app)

## Phase 4 — Discovery & Matching
- Job Discovery Agent (career pages, RSS, public APIs — no ToS-violating scraping)
- JD Parser, Company Research Agent, semantic Matching Agent

## Phase 5 — Resume & Application Materials
- Resume Optimization Agent (truthful keyword alignment, no fabrication)
- ATS Validation Agent, Cover Letter Generator

## Phase 6 — Application Assistant
- Playwright-based browser automation for supported ATS platforms
- Mandatory human-approval gate before any submission
- Application Tracker

## Phase 7 — Dashboard & Intelligence
- User dashboard (applications, interviews, outcomes)
- Learning & Analytics agent: resume performance, skill-gap signals, response-rate trends

## Phase 8 — Production Hardening
- Kubernetes deployment, autoscaling, Terraform-managed infra
- Prometheus/Grafana monitoring, alerting, structured logging, backups & disaster recovery
- Security review, load testing, cost optimization

## v1.0 — Stable Release
Multi-agent pipeline, resume optimization, job matching, human-approved application assistance, dashboard, analytics, cloud deployment, and complete documentation.

## Success Metrics
| Metric | Target (post-v1.0) |
|---|---|
| Time to review a ready application | < 2 minutes |
| ATS keyword alignment score | Consistently improved vs. baseline resume |
| False/fabricated content in generated materials | Zero tolerance — automated checks required |
| Application tracking coverage | 100% of submitted applications logged |

## Risks to Watch
- Source platforms blocking or rate-limiting automated discovery
- ATS UI changes breaking browser automation
- LLM cost scaling with per-application generation
- Legal/ToS compliance across third-party platforms
