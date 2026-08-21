# 🤖 AI Job Agent

> **An Autonomous AI-Powered Career Operating System**
>
> AI Job Agent is a cloud-native, multi-agent platform that continuously discovers relevant job opportunities, intelligently tailors application materials, and assists users throughout the hiring process. Running 24/7, it transforms the traditionally manual job search into an automated, data-driven workflow while keeping the user in control of critical decisions.

[![CI](https://github.com/OWNER/AI-Job-Agent/actions/workflows/ci.yml/badge.svg)](https://github.com/OWNER/AI-Job-Agent/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Docs](https://img.shields.io/badge/docs-available-blue.svg)](docs/)

---

## 📖 Overview

Modern hiring involves hundreds of job portals, multiple Applicant Tracking Systems (ATS), resume customization, cover letters, eligibility filtering, company research, application tracking, and interview preparation. AI Job Agent automates these repetitive tasks using a network of specialized AI agents.

## 🎯 Objectives

- Discover jobs automatically across boards, ATS platforms, and career pages
- Match jobs to the user's profile using semantic AI
- Optimize resumes for every job, truthfully and without fabrication
- Generate personalized cover letters
- Assist with (human-approved) applications
- Track application history and outcomes
- Learn from outcomes to improve future recommendations

## 🧠 Core Features

| Feature | Description |
|---|---|
| Intelligent Job Discovery | Continuous monitoring of LinkedIn, Greenhouse, Lever, Ashby, Workday, career pages, RSS feeds |
| AI Job Matching | Semantic scoring against skills, experience, location, and preferences |
| Resume Intelligence | ATS-aware, keyword-aligned resume tailoring with zero fabrication |
| Cover Letter Generation | Company- and role-specific personalized drafts |
| Application Assistant | Browser-automated form filling with mandatory human approval gates |
| Dashboard & Analytics | Applications, interviews, rejections, resume performance |
| Career Intelligence | Long-term trend analysis across resumes, skills, and companies |

## 🏗 System Architecture

See [ARCHITECTURE.md](ARCHITECTURE.md) for the full breakdown.

```
Scheduler → Job Discovery / Company Research / JD Parser → Matching Agent
   → Resume Optimization → Cover Letter Generator → ATS Validation
   → Application Assistant (human approval) → Application Tracker
   → Learning & Analytics → User Dashboard
```

## ⚙ Technology Stack

See [TECH_STACK.md](TECH_STACK.md) for the full breakdown and rationale.

Backend: Python, FastAPI, PostgreSQL, Redis, Celery · AI: LLM + embeddings + reranking ·
Automation: Playwright · Infra: Docker, Kubernetes, GitHub Actions · Cloud: AWS/GCP/Azure

## 📂 Repository Structure

```
AI-Job-Agent/
├── docs/                  # Research, architecture, agent specs, API/DB docs
├── backend/                # FastAPI application, agents, services
├── tests/                  # Unit, integration, e2e tests
├── deployment/              # Docker, Kubernetes, Terraform
├── monitoring/               # Prometheus, Grafana, alerting rules
├── scripts/                  # Dev and ops scripts
└── .github/                  # CI/CD workflows, issue/PR templates
```

## 🚀 Getting Started

```bash
git clone https://github.com/OWNER/AI-Job-Agent.git
cd AI-Job-Agent
cp .env.example .env
make setup
make up
```

See [DEVELOPMENT_GUIDE.md](DEVELOPMENT_GUIDE.md) for full local setup, testing, and workflow instructions.

## 🛣 Roadmap

See [ROADMAP.md](ROADMAP.md) for phased milestones from foundation through production.

## 🔒 Security

The project prioritizes secure authentication, encrypted secrets, least-privilege access, and mandatory human approval for any external submission action. See [SECURITY.md](SECURITY.md).

## 🤝 Contributing

Contributions are welcome — please read [CONTRIBUTING.md](CONTRIBUTING.md) and [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) first.

## 📜 License

Licensed under the [MIT License](LICENSE).

## ⚠ Disclaimer

AI Job Agent assists users throughout the job search process. Users remain responsible for reviewing application materials, ensuring their accuracy, and making final submission decisions. Resume tailoring must reflect the user's real qualifications, and interactions with third-party platforms must comply with their applicable terms of service.

## ⭐ Project Status

**Current Stage:** Phase 1 — Foundation (repository scaffolding, governance, and tooling)
