# Contributing to AI Job Agent

Thank you for your interest in contributing! We welcome contributions from developers, researchers, designers, DevOps engineers, AI practitioners, and technical writers.

## Table of Contents
- [Code of Conduct](#code-of-conduct)
- [Ways to Contribute](#ways-to-contribute)
- [Getting Started](#getting-started)
- [Branch & Commit Conventions](#branch--commit-conventions)
- [Pull Request Guidelines](#pull-request-guidelines)
- [Coding Standards](#coding-standards)
- [AI Agent Development Guidelines](#ai-agent-development-guidelines)
- [Testing Requirements](#testing-requirements)
- [Reporting Bugs & Suggesting Features](#reporting-bugs--suggesting-features)
- [Security Issues](#security-issues)

## Code of Conduct
By participating, you agree to follow our [Code of Conduct](CODE_OF_CONDUCT.md).

## Ways to Contribute
- **Code:** backend, frontend, agents, automation, APIs, infrastructure
- **Documentation:** README, architecture, API docs, tutorials, deployment guides
- **Research:** hiring platforms, ATS systems, resume optimization, LLM evaluation
- **Testing:** unit, integration, end-to-end, agent evaluations

## Getting Started
```bash
git clone https://github.com/<your-username>/AI-Job-Agent.git
cd AI-Job-Agent
git checkout -b feature/job-parser
cp .env.example .env
make setup
make test
git push origin feature/job-parser
```
Never work directly on `main`. Open a Pull Request describing what changed, why, and any related issues.

## Branch & Commit Conventions

**Branches:** `feature/*`, `bugfix/*`, `docs/*`, `refactor/*`, `test/*`

**Commits** follow [Conventional Commits](https://www.conventionalcommits.org/):
```
feat(resume): improve ATS keyword extraction
fix(api): resolve duplicate application issue
docs: update deployment guide
refactor(parser): simplify extraction pipeline
```

## Pull Request Guidelines
Every PR should solve one problem, include documentation when needed, pass all CI checks, follow coding standards, and be reviewed before merging. Large, unfocused PRs are discouraged.

## Coding Standards

**Python:** PEP 8, formatted with `black`, linted with `ruff`, type hints required, docstrings on public functions.

**API:** RESTful design, correct HTTP status codes, consistent JSON responses, input validation via Pydantic.

**Database:** meaningful table/column names, explicit relationships, indexed search fields, migrations required for schema changes.

## AI Agent Development Guidelines
Every agent must document: purpose, inputs, outputs, prompt, memory, tools, failure handling, retry strategy, and logging. Avoid embedding business logic directly into prompts — keep prompts declarative and logic in code.

Agents must **never** fabricate experience, skills, degrees, or certifications when generating resumes or cover letters.

## Testing Requirements
New features require appropriate tests (unit, integration, and/or agent evaluation). Untested code is unlikely to be merged. Run the full suite before opening a PR:
```bash
make test
```

## Reporting Bugs & Suggesting Features
Include OS, Python version, browser (if applicable), steps to reproduce, expected vs. actual behavior, and logs/screenshots. Feature requests should explain the problem, proposed solution, alternatives considered, and expected benefit.

## Security Issues
**Do not** report security vulnerabilities via public issues. Follow the process in [SECURITY.md](SECURITY.md).

---
Thank you for contributing! 🚀


## AI Job Agent release and evidence rules

- Read [the documentation index](docs/DOCUMENTATION_INDEX.md), [release runbook](docs/operations/RELEASE_RUNBOOK.md), and the latest dated release audit before release-related changes.
- Run the applicable tests; report checks that are blocked or skipped rather than calling them passed.
- Keep the frozen benchmark artifact byte-for-byte stable. Reconcile SHA-256 and provenance before using it in CI; never overwrite adjudicated labels with a provisional workbook.
- Synthetic benchmark IDs must not be guessed into production IDs. Use an authorized read-only export, preserve its SHA-256, and independently review mappings.
- Production ranking metrics must come from the runtime ranker over verified persisted jobs. Do not promote a baseline by manually editing an authority flag.
- Preserve historical audit reports as evidence snapshots. Correct current status with explicit evidence rather than rewriting history.
- Never commit production secrets, raw resumes, personal data, or unredacted production logs.
