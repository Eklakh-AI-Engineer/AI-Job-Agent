# Documentation Index

This page is the navigation map for current technical documentation. Dated audit reports are evidence snapshots, not a substitute for current code or a fresh verification run.

## Start here

| Need | Canonical document |
|---|---|
| Product scope, quick orientation, major links | [Repository README](../README.md) |
| Architecture and system boundaries | [Architecture](ARCHITECTURE.md) |
| Local environment and development commands | [Development guide](DEVELOPMENT.md) |
| Security controls and known boundaries | [Security](SECURITY.md) |
| Contribution and validation expectations | [Contributing](../CONTRIBUTING.md) |
| Release gates and release order | [Release runbook](operations/RELEASE_RUNBOOK.md) |
| Latest dated release evidence snapshot | [Release audit, 2026-10-09](operations/RELEASE_AUDIT_2026-10-09.md) |
| Deployment topology and environment variables | [Vercel / Render / Supabase](deployment/VERCEL_RENDER_SUPABASE.md) |
| Ranking benchmark lifecycle and promotion | [Evaluation guide](evaluation/README.md) |
| Machine-readable benchmark state | [Benchmark status](evaluation/benchmark_status.json) |
| Frontend live-QA procedure | [Frontend live QA](testing/FRONTEND_LIVE_QA.md) |
| Operational hardening status | [Observability](OBSERVABILITY.md) |
| Remaining engineering/validation backlog | [Pending implementation plan](../PENDING_IMPLEMENTATION_PLAN.md) |
| User-visible changes | [Changelog](../CHANGELOG.md) |

## Source-of-truth rules

1. Runtime behavior is established by source code and tests, not prose.
2. Workflow status is established by the exact GitHub Actions run and commit.
3. Deployment status is established by observed deployment metadata and live probes.
4. Benchmark lifecycle status must match the actual workbook/dataset bytes, SHA-256, label schema, and provenance.
5. A production ranking baseline must come from the runtime ranker evaluated against verified persisted jobs. Synthetic/reference metrics are not production evidence.
6. The release decision is governed by [the release runbook](operations/RELEASE_RUNBOOK.md) and evidence captured in the current release audit.
7. Do not rewrite old dated audits to make historical status appear better. Add a new dated audit or amend the current status document with an explicit correction and evidence.
8. Do not remove a historical plan, audit, or artifact until references have been checked and its evidence value assessed.

## Repository hygiene

- Keep generated outputs and temporary reports out of source control unless they are intentional, reproducible release artifacts.
- Keep `.env` and secret-bearing configuration out of Git; maintain safe placeholders in `.env.example`.
- Preserve dependency lockfiles and verify clean installs in CI.
- Do not commit raw production candidate data or unredacted logs.
- Keep one clear canonical instruction for each operational workflow; link to it instead of copying it into several documents.
