# AI Job Agent Roadmap

## Current milestone

The repository has completed a broad implementation expansion from the original backend foundation. The current task tracker is [PENDING_IMPLEMENTATION_PLAN.md](../PENDING_IMPLEMENTATION_PLAN.md).

## Implemented milestones

- 🟢 FastAPI, auth, persistence, migrations and tests
- 🟢 PostgreSQL + pgvector and Redis + Celery
- 🟢 Candidate KB and deterministic candidate-job evaluation
- 🟢 Greenhouse, Lever, Workday and Apify discovery infrastructure
- 🟢 embeddings and semantic/hybrid retrieval
- 🟢 document generation workflow and ATS analysis
- 🟢 application lifecycle, audit and human-gated Playwright automation
- 🟢 Next.js agent-oriented frontend
- 🟢 Prometheus metrics, CodeQL and container publishing
- 🟢 Kubernetes/Terraform deployment scaffolding

## Critical remaining path

```text
Repository correctness
  -> Real JD extraction
  -> Canonical JobPosting pipeline
  -> Candidate-job ranking
  -> Golden evaluation set + metrics
  -> Professional PDF/DOCX artifacts
  -> Controlled ATS E2E
  -> Full product E2E
  -> CI release gate
  -> Production hardening
```

## Remaining phases

- 🔴 P0 Repository correctness
- 🔴 P1 Real job intelligence
- 🔴 P2 Candidate-job ranking
- 🔴 P3 Evaluation
- 🔴 P4 Professional documents
- 🔴 P5 Application validation
- 🔴 P6 Full E2E
- 🟠 P7-P10 CI, frontend integration, production hardening and security
- 🟡 P11 Analytics / learning loop
- 🟠 P12 Portfolio-grade engineering evidence
- 🏁 P13 v1 release gate

The older Revised implementation plan remains as a historical milestone record and is not the current pending-work list.