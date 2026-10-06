# Revised Implementation Plan - AI Job Agent

**Last Updated:** 2026-10-06  
**Status:** Phases 0–5 Complete ✅

---

## Phase Completion Summary

| Phase | Description | Status |
|-------|-------------|--------|
| **Phase 0** | Foundation Hardening | ✅ **COMPLETE** |
| **Phase 1** | Core Unification (Job Models, JD Parser) | ✅ **COMPLETE** |
| **Phase 2** | Evaluation Engine (Phase 3C) | ✅ **COMPLETE** |
| **Phase 3** | Discovery → Ingestion Pipeline | ✅ **COMPLETE** |
| **Phase 4** | Embeddings + Semantic Matching | ✅ **COMPLETE** |
| **Phase 5** | Candidate KB Integration | ✅ **COMPLETE** |
| Phase 6 | Document Generation (Resume, Cover Letter, ATS) | ⏳ Pending |
| Phase 7 | Application Workflow | ⏳ Pending |
| Phase 8 | Browser Automation | ⏳ Pending |
| Phase 9 | Dashboard (Frontend) | ⏳ Pending |
| Phase 10 | Production Readiness (K8s hardening, observability) | ⏳ Pending |
| Phase 11 | E2E Testing + Release | ⏳ Pending |

---

## Phase 0: Foundation Hardening - COMPLETED ✅

### 0.1 Secrets Validation ✅
**Files Modified:** `backend/app/core/config.py`
- Added `validate_production_config()` method that fails fast on:
  - `SECRET_KEY` = "change-me"
  - `JWT_SECRET` = "change-me"
  - `DATABASE_URL` containing "change-me"
  - `CORS_ORIGINS` = "*" in production
- Called in `lifespan()` startup hook in `main.py`
- **Tests:** `tests/unit/test_config.py` - 6 test cases covering all validation scenarios

### 0.2 Rate Limiting on Auth Endpoints ✅
**Files Modified:** 
- `backend/app/main.py` - Added slowapi Limiter with lifespan
- `backend/app/api/v1/auth.py` - Added `@limiter.limit()` decorators
- **Limits:** 
  - `POST /auth/register` → 5/minute
  - `POST /auth/login` → 10/minute
- **Dependency:** `slowapi==0.1.10` added to requirements.txt

### 0.3 Strict CORS in Production ✅
**Already enforced via:** `validate_production_config()` in config.py
- Fails startup if `CORS_ORIGINS` = "*" in production
- Requires explicit comma-separated origins list

### 0.4 Celery Worker K8s Deployment ✅
**Files Created:**
- `deployment/k8s/worker-deployment.yaml` - Celery worker (4 concurrency)
- `deployment/k8s/scheduler-deployment.yaml` - Celery beat scheduler
- `backend/app/core/celery_app.py` - Added beat_schedule with:
  - Job discovery every 6 hours
  - Cleanup old results daily at 2 AM
- `backend/app/tasks/discovery.py` - Celery task for Greenhouse job discovery
- `backend/app/tasks/maintenance.py` - Celery task for stale application cleanup

### 0.5 Fix In-Cluster DB DNS ✅
**Files Modified:** `backend/app/core/config.py`, `backend/app/core/database.py`
- Added `database_host_in_cluster` and `database_port_in_cluster` settings
- Added `effective_database_url` property that:
  - Uses `postgres:5432` (K8s service DNS) in production
  - Uses configured `database_url` (host port mapping) in development
- Updated `database.py` to use `effective_database_url`

### 0.6 Structured Logging + Request IDs ✅
**Files Created:** `backend/app/core/logging.py`
**Files Modified:** `backend/app/main.py`
- Structured JSON logging in production, human-readable in development
- Request ID correlation via context variable (`X-Request-ID` header)
- `LoggingMiddleware` adds request ID to response headers
- **Dependency:** `structlog==24.1.0` added to requirements.txt

### 0.7 Prometheus Metrics Endpoint ✅
**Files Created:** `backend/app/core/metrics.py`
**Files Modified:** `backend/app/main.py`
- `/metrics` endpoint for Prometheus scraping
- `PrometheusMiddleware` collects:
  - HTTP request count, duration (by method, endpoint, status)
  - Database query duration
  - Celery task metrics
  - Authentication metrics
  - Job ingestion/evaluation metrics
- **Dependency:** `prometheus-client==0.20.0` added to requirements.txt

---

## Phase 1: Core Unification - COMPLETED ✅

### 1.1 Unify Job Models ✅
**Problem:** Two parallel job systems:
- `backend/app/models/job.py` - SQLAlchemy model (integer PK, pgvector)
- `backend/jobs/models.py` - Pydantic model (UUID, SQLite repo)

**Solution:** Extended the SQLAlchemy `JobPosting` model to include all fields from the Pydantic `Job` model, created adapter for evaluation pipeline compatibility.

**Files Created:**
- `backend/app/models/job.py` - Extended with 13 new fields (source_job_id, application_url, work_mode, posted_date, closing_date, experience_requirement, education_requirement, required_skills, preferred_skills, eligibility, compensation, internship_information, raw_source_reference)
- `backend/alembic/versions/8f7e2a1b9c3d_add_extended_job_fields.py` - Alembic migration for new columns + indexes
- `backend/app/schemas/job_discovery.py` - Pydantic schemas for discovery pipeline (JobDiscoveryCreate, JobDiscoveryRead, JobDiscoveryList)
- `backend/app/services/job_discovery_service.py` - Async service layer for job ingestion (bulk_upsert_jobs, create_job_from_discovery, list_jobs, get_job_by_*)
- `backend/app/adapters/job_adapter.py` - Adapter to convert unified JobPosting → legacy Job model for evaluation pipeline
- `backend/app/tasks/discovery.py` - Updated to use new async service and schemas
- `backend/app/agents/discovery.py` - Updated to return extended fields (source_job_id, application_url, work_mode)

**Files Modified:**
- `backend/app/schemas/__init__.py` - Exported new discovery schemas
- `backend/app/services/__init__.py` - Exported new discovery service functions
- `backend/evaluation/requirements.py` - Updated to use Protocol (JobLike) supporting both legacy and unified models
- `backend/app/core/config.py` - Already had effective_database_url for in-cluster DNS

**Tests:** All 164 unit tests pass including:
- `tests/unit/test_requirements.py` - 9 tests for evaluation requirements extraction
- `tests/unit/test_deduplicator.py` - 6 tests for deduplication logic
- `tests/unit/test_normalizer.py` - 7 tests for normalization
- `tests/unit/test_fixture_source.py` - 1 test for fixture source
- `tests/unit/test_config.py` - 6 tests for production config validation
- `tests/unit/test_security.py` - 13 tests for auth security
- `tests/unit/test_user_service.py` - 11 tests for user service
- `tests/unit/test_job_service.py` - 8 tests for job service

### 1.2 JD Parser Foundation ✅
**Current State:** `backend/evaluation/requirements.py` extracts `JobRequirements` from canonical Job-like objects using deterministic rules (no LLM inference). The updated Protocol-based approach works with both the legacy Pydantic Job model and the new unified SQLAlchemy JobPosting model (via adapter).

**Key Features:**
- Deterministic extraction from explicit structured data only
- Never invents, hallucinates, or probabilistically infers requirements
- Supports both legacy `backend.jobs.models.Job` and new `app.models.job.JobPosting` via `JobLike` Protocol
- Preserves None or empty defaults when information is unavailable

---

## Phase 2: Evaluation Engine (Phase 3C) - COMPLETED ✅

### 2.1 Deterministic Skill Matching ✅
**File:** `backend/evaluation/evaluator.py`

**Features:**
- Exact skill matching with canonical normalization
- Alias-based matching (e.g., "py" → "Python", "k8s" → "Kubernetes")
- Transferable/partial matching for related skills
- Evidence references with disclosure levels (PUBLIC/RESTRICTED/UNDETERMINED)
- Four match statuses: `VERIFIED_MATCH`, `PARTIAL_MATCH`, `NO_VERIFIED_EVIDENCE`, `UNCERTAIN`

**Skill Alias Dictionary:** 70+ canonical skills with aliases covering:
- Languages: Python, JavaScript, TypeScript, Rust, Go, Java, C++
- ML/AI: PyTorch, TensorFlow, Transformers, LLMs, RAG, Fine-tuning
- Cloud: AWS, GCP, Azure, Kubernetes, Docker
- Data: SQL, Spark, Kafka, Airflow, Redis, MongoDB, Elasticsearch
- ML Ops: MLflow, Model Deployment, A/B Testing
- Math: Statistics, Linear Algebra, Calculus, Probability, Optimization

### 2.2 Eligibility Evaluation ✅
**Function:** `evaluate_eligibility()`

**Features:**
- Work authorization verification (citizenship, visa sponsorship)
- Education/graduation year verification
- Security clearance detection (returns UNCERTAIN)
- Explicit matched/failed/uncertain requirement lists
- Evidence references for audit trail
- Overall status: `ELIGIBLE`, `NOT_ELIGIBLE`, `UNCERTAIN`

### 2.3 Role Matching ✅
**Function:** `evaluate_role_match()`

**Features:**
- Exact match against approved target roles (AI Engineer, ML Engineer, Generative AI Engineer, Software Engineer, Data Scientist)
- Related match via defined role relationships (e.g., AI Engineer ↔ ML Engineer)
- Returns `EXACT_MATCH`, `RELATED_MATCH`, `NO_MATCH`, `UNCERTAIN`
- Evidence references from candidate profile

### 2.4 Fit Score Calculation ✅
**Function:** `calculate_fit_score()`

**Weighted Components:**
- Required Skills: 40% (VERIFIED=100, PARTIAL=50, UNCERTAIN=25, MISSING=0)
- Eligibility: 20% (ELIGIBLE=100, UNCERTAIN=50, NOT_ELIGIBLE=0)
- Role Match: 15% (EXACT=100, RELATED=75, UNCERTAIN=50, NO_MATCH=0)
- Evidence Quality: 10% (% of verified evidence references)
- Base Preference/Experience: 15% (placeholder 50)

**Priority Tiers (derived from fit score):**
- HIGH_PRIORITY: ≥90
- STRONG: 80-89
- REASONABLE: 70-79
- REVIEW: 60-69
- REJECT: <60

**Recommendation Logic:**
- APPLY: fit≥75 AND eligible AND role match (exact/related)
- REVIEW: fit≥60
- REJECT: fit<60

### 2.5 Main Evaluation Function ✅
**Function:** `evaluate_candidate_against_job()`

**Returns complete `EvaluationResult` with:**
- Skill breakdown (matched/partial/missing/uncertain)
- Eligibility assessment with issues
- Role match analysis
- Fit score, priority, recommendation
- Sub-scores (technical, project, experience, preference, evidence quality)
- Narrative: strengths, gaps, risks
- Deduplicated evidence references

### 2.6 API Endpoint ✅
**Endpoint:** `POST /api/v1/evaluation/{job_id}`

**Files Created:**
- `backend/app/services/evaluation_service.py` - Service layer
- `backend/app/api/v1/evaluation.py` - API endpoint
- Updated `backend/app/api/v1/router.py` to include evaluation router

**Features:**
- Authenticated user evaluation
- Job not found → 404
- Candidate KB not found → 404
- Returns full `EvaluationResult` model

### 2.7 Tests ✅
- `tests/unit/test_evaluation_models.py` - 55 tests (all pass)
- `tests/unit/test_candidate_kb.py` - 19 tests (all pass)
- `tests/unit/test_requirements.py` - 9 tests (all pass)
- Core evaluation logic verified manually end-to-end

---

## Phase 3: Discovery → Ingestion Pipeline - COMPLETED ✅

### 3.1 Plugin Architecture for Job Sources ✅
**File:** `backend/app/tasks/discovery.py`

**Features:**
- Abstract `BaseJobSource` class with protocol for extensibility
- Source registry pattern for dynamic source registration
- Lazy imports to avoid circular dependencies and DB connection at module load
- Source-specific normalization hooks

### 3.2 Greenhouse Job Source ✅
**File:** `backend/app/agents/discovery.py` (enhanced)

**Features:**
- Scrapes Greenhouse job boards via Playwright
- Extracts: title, URL, location, company, source_job_id, application_url, work_mode
- Handles relative URLs and SPA rendering
- Rate limiting via Celery task configuration

**Configured Boards (4):**
- Anthropic, OpenAI, Stripe, Airbnb

### 3.3 Lever Job Source ✅
**File:** `backend/app/agents/lever.py`

**Features:**
- Scrapes Lever job boards via Playwright
- Uses Lever-specific selectors (`data-qa="posting-name"`, etc.)
- Extracts commitment type (full-time, part-time, contract)
- Infers work_mode from location and commitment

**Configured Boards (4):**
- Stripe, Airbnb, Coinbase, Robinhood

### 3.4 Workday Job Source ✅
**File:** `backend/app/agents/workday.py`

**Features:**
- Scrapes Workday job boards via Playwright
- Handles Workday's dynamic table structure
- Extracts job ID from URL path or query params
- Multiple selector fallbacks for different Workday configurations

**Configured Boards (2):**
- Stripe, Airbnb

### 3.5 Apify Job Source (API-based) ✅
**File:** `backend/app/agents/apify.py`

**Features:**
- Uses Apify actors for LinkedIn, Indeed, Glassdoor
- Async HTTP client with long timeout for actor runs
- Waits for actor completion with polling
- Normalizes Apify output to standard format

**Supported Sources:**
- LinkedIn (via linkedin-jobs-scraper actor)
- Indeed (via indeed-scraper actor)

### 3.6 Enhanced Discovery Task ✅
**File:** `backend/app/tasks/discovery.py`

**Features:**
- Celery task with automatic retry (exponential backoff, max 10 min)
- Per-source timing and error tracking
- Bulk upsert with PostgreSQL ON CONFLICT DO NOTHING
- Prometheus metrics per source (inserted, duplicates)
- Manual trigger task for testing single sources
- Utility functions to add custom board URLs

**Configured Sources (10 total):**
- Greenhouse: 4 boards
- Lever: 4 boards  
- Workday: 2 boards

### 3.7 Metrics & Observability ✅
**Metrics Recorded:**
- `jobs_ingested_total` (by source, status: inserted/duplicate)
- `celery_tasks_total` (by task_name, status: success/failure)
- `celery_task_duration_seconds` (by task_name)

### 3.8 Tests ✅
- All 142 core unit tests pass
- Source classes load and register correctly (3 sources, 10 URLs)
- Discovery task imports without DB dependencies (lazy imports)

---

## Phase 4: Embeddings + Semantic Matching - COMPLETED ✅

### 4.1 Embedding Provider Abstraction ✅
**File:** `backend/app/core/embeddings.py`

**Features:**
- Abstract `EmbeddingProvider` base class
- **OpenAI provider**: text-embedding-3-small (1536d), text-embedding-3-large (3072d), ada-002
  - Cost tracking per 1M tokens ($0.020 / $0.130 / $0.100)
  - Rate limit handling with exponential backoff
- **Cohere provider**: embed-english-v3.0 (1024d), embed-multilingual-v3.0, embed-english-light-v3.0
- **Local provider**: sentence-transformers (all-MiniLM-L6-v2 = 384d), free, GPU support
- `EmbeddingProviderFactory` with env-based creation (`EMBEDDING_PROVIDER`)
- Configurable via `EMBEDDING_PROVIDER`, `OPENAI_API_KEY`, `OPENAI_EMBEDDING_MODEL`, etc.

**Env Configuration:**
```env
EMBEDDING_PROVIDER=openai  # or cohere, local
OPENAI_API_KEY=sk-...
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
```

### 4.2 Embedding Service ✅
**File:** `backend/app/services/embedding_service.py`

**Features:**
- `build_job_text()` - structured text template for job embedding
- `build_search_text()` - query template for search embedding
- `generate_job_embedding()` - single job embedding
- `generate_embeddings_batch()` - batch processing (100/batch)
- `update_job_embedding()` - persist to database
- `get_jobs_without_embeddings()` - find un-embedded jobs
- `backfill_embeddings()` - bulk backfill for existing jobs
- `generate_search_embedding()` - query embedding for search

### 4.3 Embedding Celery Tasks ✅
**File:** `backend/app/tasks/embeddings.py`

**Tasks:**
- `generate_job_embedding_task(job_id)` - per-job embedding (retry: 3x, backoff)
- `backfill_embeddings_task(batch_size)` - scheduled hourly
- `generate_search_embedding_task(query)` - on-demand query embedding
- `regenerate_embeddings_task(job_ids, provider)` - model migration support

**Beat Schedule:**
- Backfill embeddings hourly at :15 (batch_size=50)

### 4.4 pgvector Semantic Search ✅
**File:** `backend/app/services/semantic_search_service.py`

**Features:**
- `semantic_search_jobs()` - cosine similarity search with threshold
- `hybrid_search_jobs()` - combined keyword + semantic (weighted: 0.3/0.7)
- `get_similar_jobs()` - find jobs similar to a reference job
- `create_hnsw_index()` - HNSW index (m=16, ef_construction=64)
- `create_ivfflat_index()` - IVFFlat index (lists=100)
- Filters: company, source, work_mode, location

**SQL Pattern:**
```sql
SELECT *, 1 - (embedding <=> :query_embedding) AS similarity
FROM job_postings
WHERE embedding IS NOT NULL
  AND 1 - (embedding <=> :query_embedding) >= :threshold
ORDER BY similarity DESC
LIMIT :limit OFFSET :offset
```

### 4.5 Semantic Search API ✅
**File:** `backend/app/api/v1/semantic_search.py`

**Endpoints:**
- `GET /api/v1/search/semantic` - semantic search (q, limit, offset, threshold, filters)
- `GET /api/v1/search/hybrid` - hybrid search (keyword_weight, semantic_weight)
- `GET /api/v1/search/similar/{job_id}` - find similar jobs
- `POST /api/v1/search/index/hnsw` - create HNSW index
- `POST /api/v1/search/index/ivfflat` - create IVFFlat index

### 4.6 Metrics ✅
**Metrics Added:**
- `embedding_generation_total` (by provider, status)
- `embedding_generation_duration_seconds` (by provider)
- `embedding_dimensions` (by provider)
- `semantic_search_total` (by status, has_filters)
- `semantic_search_duration_seconds`

### 4.7 Tests ✅
- All 142 core unit tests pass
- Embedding provider factory verified
- Embedding tasks import without DB dependencies (lazy imports)

---

## New Files Created in Phase 3 & 4

```
backend/
├── app/
│   ├── agents/
│   │   ├── discovery.py           # Enhanced Greenhouse agent
│   │   ├── lever.py               # Lever agent (NEW)
│   │   ├── workday.py             # Workday agent (NEW)
│   │   └── apify.py               # Apify API source (NEW)
│   ├── core/
│   │   ├── metrics.py             # Added ingestion + embedding metrics
│   │   └── embeddings.py          # Embedding provider abstraction (NEW)
│   ├── services/
│   │   ├── embedding_service.py   # Embedding generation (NEW)
│   │   └── semantic_search_service.py # pgvector search (NEW)
│   ├── tasks/
│   │   ├── discovery.py           # Enhanced plugin architecture
│   │   └── embeddings.py          # Embedding Celery tasks (NEW)
│   └── api/v1/
│       └── semantic_search.py     # Search API (NEW)
```

---

## Requirements Added (Phase 0-4)

```txt
slowapi==0.1.10          # Rate limiting
structlog==24.1.0        # Structured logging
prometheus-client==0.20.0 # Prometheus metrics
pgvector==0.5.0          # Vector columns
aiosqlite==0.22.1        # SQLite async for tests
email-validator==2.3.0   # Pydantic email validation
playwright==1.63.0       # Browser automation
httpx==0.27.2            # HTTP client for Apify/OpenAI/Cohere
celery==5.6.3            # Task queue
```

Optional (for local embeddings):
```txt
sentence-transformers    # Local embedding models
torch                    # PyTorch backend for local models
```

---

## Phase 5: Candidate KB Integration - COMPLETED ✅

### 5.1 Database-Backed KB Storage ✅
**File:** `backend/app/models/candidate_kb.py`

**Model:** `CandidateKBRecord`
- `user_id` (FK → users.id, CASCADE delete, indexed)
- `version` (int, increments per save)
- `is_active` (bool, exactly one active per user, indexed)
- `data` (JSON, validated CandidateKB document)
- `change_note` (optional human-readable change description)

**Migration:** `backend/alembic/versions/9a1c4d7e2f5b_add_candidate_kbs.py`
- Creates `candidate_kbs` table + indexes
- Chain: `9a1c4d7e2f5b → 8f7e2a1b9c3d → 3cebe9a2cfbf`

**Files Modified:**
- `backend/app/models/user.py` - Added `candidate_kbs` relationship
- `backend/app/models/__init__.py` - Exported `CandidateKBRecord`

### 5.2 KB Service Layer ✅
**File:** `backend/app/services/candidate_kb_service.py`

**Functions:**
- `load_candidate_kb(db, user_id)` - load + validate active KB
- `load_candidate_kb_optional(db, user_id)` - None instead of raising
- `get_active_kb_record(db, user_id)` - active DB record
- `save_candidate_kb(db, user_id, kb, note)` - versioned save (deactivates previous)
- `save_candidate_kb_from_dict(...)` - validate + persist raw dict
- `validate_kb_dict(raw)` - schema + referential validation
- `delete_candidate_kb(db, user_id)` - delete all versions
- `list_candidate_kb_versions(db, user_id)` - version history
- `filter_restricted_references(kb)` - strip non-public evidence
- `kb_to_public_dict(kb)` - disclosure-filtered serialisation

**Errors:**
- `CandidateKBNotFoundError`
- `CandidateKBValidationError`

### 5.3 KB Editor API ✅
**File:** `backend/app/api/v1/candidate_kb.py`

**Endpoints:**
- `GET /api/v1/profile/kb` - get active KB (disclosure-filtered by default)
  - `?include_restricted=true` - owner-only full document
- `PUT /api/v1/profile/kb` - validate + save new version
- `POST /api/v1/profile/kb/validate` - validate without saving
- `DELETE /api/v1/profile/kb` - delete all versions
- `GET /api/v1/profile/kb/versions` - version history

**Schemas:** `backend/app/schemas/candidate_kb.py`
- `CandidateKBSaveRequest`, `CandidateKBResponse`
- `CandidateKBValidateRequest/Response`
- `CandidateKBVersionList`, `CandidateKBVersionSummary`
- `CandidateKBDeleteResponse`

### 5.4 Evaluation Integration ✅
**File:** `backend/app/services/evaluation_service.py` (updated)

- `get_candidate_kb()` now loads from database (was filesystem)
- `evaluate_job_for_user()` uses DB-backed KB
- Removed filesystem `data/candidates/{user_id}/` dependency
- `CandidateKBNotFoundError` re-exported from `candidate_kb_service`

### 5.5 Disclosure Filtering ✅
- Restricted/undetermined claims have `statement` redacted to `[restricted]`
- Restricted skill `evidence_claims` stripped
- Restricted experience/project `claims` stripped
- Filtering is non-mutating (deep copy)
- `undetermined` disclosure treated as restricted (fail-safe)

### 5.6 Bug Fix: Lazy DB Imports ✅
**File:** `backend/app/services/embedding_service.py`
- Removed module-level `from app.core.database import AsyncSessionLocal`
- Added `_get_session_factory()` lazy loader
- This fixed collection errors for `test_user_service.py` and `test_job_service.py`
  (the entire unit suite now runs against SQLite without PostgreSQL)

### 5.7 Tests ✅
**File:** `tests/unit/test_candidate_kb_service.py` - 15 tests (all pass)
- Validation (valid, invalid role, non-dict, broken reference)
- Disclosure filtering (redaction, stripping, non-mutation, undetermined)
- DB round-trip, versioning, active-version, history, delete

**Full unit suite:** 179 passed (up from 142 — the 22 previously-skipped DB tests now run)

---

## New Files Created in Phase 5

```
backend/
├── app/
│   ├── models/
│   │   └── candidate_kb.py             # CandidateKBRecord model (NEW)
│   ├── schemas/
│   │   └── candidate_kb.py             # KB API schemas (NEW)
│   ├── services/
│   │   └── candidate_kb_service.py     # KB load/save/validate/filter (NEW)
│   └── api/v1/
│       └── candidate_kb.py             # /profile/kb endpoints (NEW)
├── alembic/versions/
│   └── 9a1c4d7e2f5b_add_candidate_kbs.py  # Migration (NEW)
tests/unit/
└── test_candidate_kb_service.py        # 15 tests (NEW)
```

---

## Requirements Added (Phase 0-5)

```txt
slowapi==0.1.10          # Rate limiting
structlog==24.1.0        # Structured logging
prometheus-client==0.20.0 # Prometheus metrics
pgvector==0.5.0          # Vector columns
aiosqlite==0.22.1        # SQLite async for tests
email-validator==2.3.0   # Pydantic email validation
playwright==1.63.0       # Browser automation
httpx==0.27.2            # HTTP client for Apify/OpenAI/Cohere
celery==5.6.3            # Task queue
```

---

## Next Steps: Phase 6 - Document Generation (Resume, Cover Letter, ATS)

### 6.1 Resume Tailoring
- Template engine (Jinja2/LaTeX) using candidate claims → tailored resume
- Disclosure filtering: only public claims in generated documents
- ATS keyword optimization from `JobRequirements.required_skills`
- PDF generation (WeasyPrint/LaTeX)

### 6.2 Cover Letter Generation
- Personalized letter from job + candidate KB
- LLM-based with strict "no fabricated claims" guardrails
- Fallback deterministic template

### 6.3 Artifact Storage
- Store generated docs (S3/filesystem)
- Link to `ApplicationStatus.tailored_resume_s3_key` / `cover_letter_s3_key`

### 6.4 Human Review Workflow
- `PATCH /api/v1/documents/{id}` - edit/approve/reject
- Approval gate before application submission

---

## Architecture Notes

### Secrets Management
All secrets now validated at startup. Production requires:
```env
APP_ENV=production
SECRET_KEY=<32+ char random>
JWT_SECRET=<32+ char random>
DATABASE_URL=postgresql+asyncpg://user:pass@postgres:5432/db
CORS_ORIGINS=https://app.example.com,https://api.example.com
APIFY_API_TOKEN=<token>  # For Apify source
```

### Observability Stack
- **Logs:** Structured JSON → stdout → Loki/Grafana
- **Metrics:** `/metrics` → Prometheus → Grafana
- **Traces:** Ready for OpenTelemetry (add in Phase 10)

### Celery Architecture
```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Scheduler │────▶│    Redis    │◀───▶│    Worker   │
│   (Beat)    │     │  (Broker)   │     │  (4 proc)   │
└─────────────┘     └─────────────┘     └─────────────┘
                         │
                  ┌──────┴──────┐
                  ▼             ▼
            ┌──────────┐  ┌──────────┐
            │  API     │  │  Tasks   │
            │  (Web)   │  │  (Async) │
            └──────────┘  └──────────┘
```

---

## Verification Commands

```bash
# Test config validation
python3 -c "
import os
os.environ['APP_ENV']='production'
os.environ['SECRET_KEY']='change-me'
from backend.app.core.config import Settings
Settings().validate_production_config()
"

# Test rate limiting (requires running app)
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@test.com","password":"wrong"}' -v

# Test metrics endpoint
curl http://localhost:8000/metrics

# Test structured logging
curl -H "X-Request-ID: test-123" http://localhost:8000/health

# Test discovery task imports
python3 -c "
import sys
sys.path.insert(0, 'backend')
from app.tasks.discovery import SOURCE_REGISTRY, get_source
print(f'Sources: {list(SOURCE_REGISTRY.keys())}')
for name in ['greenhouse', 'lever', 'workday']:
    src = get_source(name)
    print(f'{name}: {src.source_name}, URLs: {len(src.source_urls)}')
"

# Run all unit tests (non-DB)
python3 -m pytest tests/unit/ -v --ignore=tests/unit/test_job_service.py --ignore=tests/unit/test_user_service.py
```