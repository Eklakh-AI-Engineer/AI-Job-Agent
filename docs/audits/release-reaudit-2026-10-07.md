# AI-Job-Agent v1 Release Re-Audit — 2026-10-07

## Executive verdict

**Release status: NOT READY FOR v1.0.0**

The repository is substantially engineered and the CI/evaluation infrastructure is now stronger, but several gates require external production evidence that cannot be truthfully fabricated from source configuration.

## Status matrix

| # | Gate | Status | Evidence / blocker |
|---|---|---|---|
| 5 | Human-label adjudication | 🔴 Blocked | 394 AI/human disagreements remain; no independent adjudication evidence |
| 6 | Real persisted-job mapping | 🔴 Blocked | Workbook uses synthetic JOB-001..JOB-100; no connected AI-Job-Agent production DB |
| 7 | Benchmark freeze + SHA-256 | 🟠 Candidate only | Candidate hash recorded; golden freeze blocked by 5/6 |
| 8 | Ranking baseline | 🟢 Complete (provisional) | baseline.json + latest.json committed; 1.0000 fixture-order reference metrics |
| 9 | Regression gate | 🟢 Enabled | CI now runs ranking_regression_gate.py unconditionally against committed artifacts |
| 10 | Backend + E2E suite | 🟢 Previously validated / current run pending | Last verified green CI run: 37646085225; true-pipeline E2E included |
| 11 | Frontend live QA | 🔴 Blocked | Requires deployed FRONTEND_URL and LIVE_API_URL |
| 12 | Real ATS dry-run evidence | 🔴 Blocked | Requires real ATS/browser target and live execution evidence |
| 13 | Vercel + Render + Supabase deployment | 🔴 Blocked | No connected Vercel team; no AI-Job-Agent Supabase project; Render credentials/access unavailable |
| 14 | Production smoke tests | 🔴 Blocked | No production deployment to test |
| 15 | Monitoring / alerts | 🟠 Partial | Prometheus metrics exist; scheduled GitHub monitoring workflow added; alert delivery not verified |
| 16 | Backup / restore | 🔴 Blocked | Production Supabase/Storage environment unavailable for restore test |
| 17 | Re-audit | 🟢 Complete | This document is the current release re-audit |
| 18 | v1.0 tag | 🔴 Blocked | Must follow completion of production and benchmark gates |

## Completed release hardening

- Ranking baseline artifacts committed.
- Regression gate changed from conditional/no-op to enforced.
- Scheduled production monitoring smoke workflow added.
- Production smoke checklist documented.
- Backup/restore acceptance criteria documented.
- Release runbook documents the evidence boundary.

## Benchmark integrity

The human benchmark remains **provisional**.

Source workbook SHA-256:
3723436be0cd843e57edf569a3661c551960f225ea7587ac1a71369909f9c5bc

Current benchmark facts:
- 500 labeled rows
- 100 synthetic job IDs
- 394 AI/human label disagreements
- independent adjudication: false
- real persisted jobs: false
- frozen: false

Therefore the benchmark must not be represented as a production-quality golden ranking dataset.

## Deployment access audit

Current connected Supabase projects are **Tackboard** and **Enterprise-RAG**; neither is AI-Job-Agent.

Vercel currently reports no connected team/project context.

The repository contains Render/Vercel/Supabase deployment configuration, but configuration is not deployment evidence.

## Release decision

**Do not create v1.0.0 yet.**

The remaining work is not primarily source-code implementation. It is evidence acquisition:

1. connect/provision the AI-Job-Agent Supabase project;
2. deploy Render API + worker and Vercel frontend;
3. execute live frontend QA;
4. execute a real ATS dry-run with captured evidence;
5. verify production smoke, metrics and alert delivery;
6. execute backup/restore;
7. obtain independent benchmark adjudication and real-job mapping;
8. replace the provisional ranking baseline with the real frozen benchmark;
9. rerun the complete release suite;
10. only then tag v1.0.0.

**No synthetic or configuration-only evidence is promoted to production evidence.**
