# AI Job Agent — Frontend

A Next.js 16 (App Router) **AI career agent** dashboard for the AI Job Agent
backend. The UI is agent-first: it surfaces recommendations, reasoning, and
automation rather than behaving like a job-listing portal.

## Agent experience

- **Command Center** (`/dashboard`) — agent presence, daily summary, action
  center, top recommendations, activity, pipeline.
- **Opportunities** (`/opportunities`) — feed bucketed into
  **Recommended / Worth reviewing / Low fit**, ranked by real fit against your
  Candidate KB, plus a **natural-language assistant**
  (*"AI Engineer roles in UAE with strong Python/LLM fit"*).
- **Application Copilot** (`/copilot`) — one guided workflow:
  choose → analyze → resume → cover letter → review & apply.
- **Document Workspace** (`/documents`) — Why-this-doc, ATS score, evidence
  used, and version history.
- **Applications** (`/applications`) — guarded kanban pipeline with dry-run and
  explicit, human-approved submission.
- **Agent Activity** (`/activity`) — real timeline of discovery → matching →
  documents → approval → application.
- **Candidate Profile** (`/profile`) — structured KB editor with validation.

Human-in-the-loop throughout: the agent recommends, you approve. It never
submits silently.

## Features (backend integration)

- JWT auth (`/api/v1/auth`), jobs, deterministic fit **evaluation**,
  hybrid/semantic **search**, Candidate **KB**, **documents**, and
  **applications** (including browser-automation dry-run/submit).


## Configuration

```bash
cp .env.local.example .env.local
# NEXT_PUBLIC_API_URL points at the FastAPI backend (default http://127.0.0.1:8000)
```

## Development

```bash
npm install
npm run dev      # http://localhost:3000
```

## Build & lint

```bash
npm run build
npm run lint
```

## Design system

The palette is defined once in `src/app/globals.css` via Tailwind v4 `@theme`
tokens and consumed through utility classes (`bg-primary`, `text-muted`,
`border-border`, etc.):

| Purpose        | Token              | Value     |
| -------------- | ------------------ | --------- |
| Primary        | `primary`          | `#2563EB` |
| Primary hover  | `primary-hover`    | `#1D4ED8` |
| Secondary      | `secondary`        | `#64748B` |
| Background     | `background`       | `#F8FAFC` |
| Card           | `card`             | `#FFFFFF` |
| Border         | `border`           | `#E2E8F0` |
| Text           | `foreground`       | `#0F172A` |
| Muted          | `muted`            | `#64748B` |
| Success        | `success`          | `#059669` |
| Warning        | `warning`          | `#D97706` |
| Danger         | `danger`           | `#DC2626` |

## Structure

```
src/
  app/
    layout.tsx                 # root layout + AuthProvider
    globals.css                # design tokens
    page.tsx                   # redirects to /dashboard or /login
    login/ register/           # auth pages
    (app)/                     # protected shell (sidebar)
      dashboard/               # Agent Command Center
      opportunities/           # Intelligent feed + NL assistant
      copilot/                 # Guided application workflow
      documents/               # Document Workspace
      applications/            # Pipeline tracker
      activity/                # Agent activity timeline
      profile/                 # Candidate KB editor
  components/                  # ui.tsx, agent.tsx, Sidebar, TopBar, icons
  lib/                         # api.ts, types.ts, auth.tsx, agent.ts, useAgentData.ts
```
