# AI Job Agent Architecture

## Current implementation boundary

The repository currently centers on a backend foundation:

```text
Client
  |
  v
FastAPI /api/v1
  |
  +--> Auth / Authorization
  |
  +--> Routers
  |
  +--> Service Layer
  |
  +--> Persistence
          |
          +--> PostgreSQL + pgvector
          +--> Redis
          +--> Alembic
```

This is the implemented foundation described by the repository's current Phase 3 status.

## Implemented responsibilities

The backend foundation provides:

- versioned API routing;
- authentication and bearer-token handling;
- user/profile access;
- job posting ingestion and retrieval;
- service-layer orchestration;
- database persistence;
- migrations;
- health checks;
- fast local tests;
- PostgreSQL integration testing.

## Target platform architecture

The broader product vision is:

```text
Job Sources
    |
    v
Job Discovery
    |
    v
Normalization / Deduplication
    |
    v
JD Parsing / Company Research
    |
    v
Candidate ↔ Job Matching
    |
    +--> Resume Optimization
    |
    +--> Cover Letter Generation
    |
    +--> ATS Validation
    |
    v
Human-Approved Application Assistance
    |
    v
Application Tracking
    |
    v
Learning / Career Analytics
```

The components after the current backend foundation should be treated as roadmap/specification work unless the corresponding implementation exists in the repository.

## Architectural controls

The system should preserve:

- human approval before external application submission;
- service-layer separation;
- explicit persistence boundaries;
- authenticated API access;
- testable deterministic components;
- no fabrication of candidate qualifications.

See the numbered architecture specifications under [02_Architecture](02_Architecture/) for deeper design material.
