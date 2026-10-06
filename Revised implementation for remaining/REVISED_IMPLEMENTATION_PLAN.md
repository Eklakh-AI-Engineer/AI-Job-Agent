# Revised Implementation Plan - AI Job Agent

**Last Updated:** 2026-10-06  
**Status:** Phases 0–9 + 9B Complete ✅

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
| **Phase 6** | Document Generation (Resume, Cover Letter, ATS) | ✅ **COMPLETE** |
| **Phase 7** | Application Workflow | ✅ **COMPLETE** |
| **Phase 8** | Browser Automation | ✅ **COMPLETE** |
| **Phase 9** | Dashboard (Frontend) | ✅ **COMPLETE** |
| **Phase 9B** | Agent Experience / Product Differentiation | ✅ **COMPLETE** |
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

## Phase 6: Document Generation (Resume, Cover Letter, ATS) - COMPLETED ✅

### 6.1 GeneratedDocument Model ✅
**File:** `backend/app/models/document.py`
- `user_id`, `job_posting_id` (FKs, CASCADE, indexed)
- `doc_type` (resume | cover_letter), `status` (draft | approved | rejected)
- `version`, `content` (rendered text), `meta` (JSON: ATS, sections)
- `used_claim_ids` (JSON audit trail), `storage_key`
- Relationships added to `User` and `JobPosting`

**Migration:** `backend/alembic/versions/b3f8c2d9e1a4_add_generated_documents.py`
- Chain: `b3f8c2d9e1a4 → 9a1c4d7e2f5b → 8f7e2a1b9c3d → 3cebe9a2cfbf`

### 6.2 Artifact Storage Abstraction ✅
**File:** `backend/app/services/document_storage.py`
- `DocumentStorage` ABC
- `LocalFilesystemStorage` (default) — with path-traversal rejection
- `S3Storage` — boto3-based, lazy import (AWS S3 / MinIO / R2)
- Backend selected via `DOCUMENT_STORAGE_BACKEND` (local | s3)
- `build_document_key()` — deterministic `users/{u}/jobs/{j}/{type}/v{n}.txt`

### 6.3 ATS Optimization Service ✅
**File:** `backend/app/services/ats_service.py`
- Deterministic keyword extraction (required first, de-duplicated)
- `analyze_ats()` — weighted score (required 70%, preferred 30%)
- Matched / missing keyword lists
- Distinguishes **addable** keywords (candidate has public evidence) from
  **unbacked** keywords ("do not fabricate")
- Multi-word phrase matching + stopword filtering

### 6.4 Resume Tailoring Service ✅
**File:** `backend/app/services/resume_service.py`
- `build_tailored_resume()` — public evidence only
- Skills ordered by job relevance; restricted skills excluded
- Experience/projects from public claims with audit trail
- Deterministic summary (no fabrication)
- Rendered plain-text, ATS-friendly output
- `used_claim_ids` records every referenced claim (public only)

### 6.5 Cover Letter Service ✅
**File:** `backend/app/services/cover_letter_service.py`
- `build_cover_letter()` — deterministic, evidence-grounded
- References matched skills + one relevant public claim as concrete example
- Education/eligibility from profile
- Never invents achievements/employers
- `used_claim_ids` audit trail

### 6.6 Orchestration + Human Review ✅
**File:** `backend/app/services/document_service.py`
- `generate_resume()` / `generate_cover_letter()` — load job + KB, extract
  requirements, generate, persist draft, store artifact (best-effort)
- `list_documents()` with job/type/status filters
- `get_document()` — ownership-scoped
- `update_document_status()` — approve/reject (human-review gate)
- `update_document_content()` — manual edit resets to draft
- `regenerate_document()` — new version

### 6.7 Document API ✅
**File:** `backend/app/api/v1/documents.py`
- `POST /api/v1/documents/generate` — generate resume/cover letter
- `GET /api/v1/documents` — list (filters: job_id, doc_type, status)
- `GET /api/v1/documents/{id}` — fetch one
- `PATCH /api/v1/documents/{id}` — manual edit (resets to draft)
- `POST /api/v1/documents/{id}/status` — approve/reject
- `POST /api/v1/documents/{id}/regenerate` — new version

**Schemas:** `backend/app/schemas/document.py`

### 6.8 Celery Tasks ✅
**File:** `backend/app/tasks/documents.py`
- `generate_document_task(user_id, job_id, doc_type)` — background generation
- `generate_all_documents_task(user_id, job_id)` — resume + cover letter

### 6.9 Disclosure Enforcement ✅
- Restricted/undetermined skills, claims, experience, projects are excluded
  from all generated documents
- Verified by tests asserting restricted content never appears in output

### 6.10 Tests ✅
**File:** `tests/unit/test_document_services.py` - 20 tests (all pass)
- ATS: keyword extraction, matching, score bounds, no-fabrication reporting
- Resume: restricted exclusion, public-only claims, relevance ordering, rendering
- Cover letter: grounding, restricted exclusion
- Storage: round-trip, path-traversal rejection
- Orchestration: draft generation, listing/filtering, approve, edit-resets-draft,
  regenerate versioning, ownership isolation, invalid status rejection

**Full unit suite:** 199 passed

---

## New Files Created in Phase 6

```
backend/
├── app/
│   ├── models/
│   │   └── document.py                 # GeneratedDocument model (NEW)
│   ├── schemas/
│   │   └── document.py                 # Document API schemas (NEW)
│   ├── services/
│   │   ├── document_storage.py         # Local/S3 artifact storage (NEW)
│   │   ├── ats_service.py              # ATS analysis (NEW)
│   │   ├── resume_service.py           # Resume tailoring (NEW)
│   │   ├── cover_letter_service.py     # Cover letter generation (NEW)
│   │   └── document_service.py         # Orchestration + review (NEW)
│   ├── api/v1/
│   │   └── documents.py                # /documents endpoints (NEW)
│   └── tasks/
│       └── documents.py                # Background generation (NEW)
├── alembic/versions/
│   └── b3f8c2d9e1a4_add_generated_documents.py  # Migration (NEW)
tests/unit/
└── test_document_services.py           # 20 tests (NEW)
```

---

## Requirements Added (Phase 0-6)

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

Optional (S3 artifact storage):
```txt
boto3                    # S3-compatible document storage
```

---

## Phase 7: Application Workflow - COMPLETED ✅

### 7.1 Extended ApplicationStatus + Audit Log ✅
**File:** `backend/app/models/job.py`
- `ApplicationStatus` extended with: `approved_at`, `applied_at`, `rejected_at`, `idempotency_key` (unique), `last_error`, `notes`, `status` index
- Unique constraint `uq_application_user_job` on `(user_id, job_posting_id)`
- New `ApplicationEvent` model — immutable append-only audit log:
  - `application_id`, `from_status`, `to_status`, `actor`, `reason`, `idempotency_key`, `event_meta`
- Relationships: `ApplicationStatus.events`

**Migration:** `backend/alembic/versions/c7d4e1a9f2b8_add_application_workflow.py`
- Chain: `c7d4e1a9f2b8 → b3f8c2d9e1a4 → 9a1c4d7e2f5b → 8f7e2a1b9c3d → 3cebe9a2cfbf`

### 7.2 Guarded State Machine ✅
**File:** `backend/app/services/application_service.py`

**States:** Discovered → Matched → Approved → Applied; terminal Rejected

**Transition table:**
```
Discovered → {Matched, Rejected}
Matched    → {Approved, Rejected}
Approved   → {Applied, Rejected}
Applied    → {Rejected}
Rejected   → {}  (terminal)
```

**Guards:**
- `Approved` requires at least one **approved resume document** for (user, job)
- `Applied` requires current status `Approved`, an approved resume still present,
  and an **idempotency key**

**Functions:** `create_application`, `get_or_create_application`,
`transition_application`, `record_event`, `list_applications`, `list_events`,
`record_submission_failure`, `is_valid_transition`

### 7.3 Idempotency + Retry ✅
- Submission requires `idempotency_key`; replaying the same key targeting the
  same status is a **no-op** (no duplicate event, state unchanged)
- `record_submission_failure()` records `last_error` + an audit event without
  changing state, so retries are safe

### 7.4 Human Approval Gate + Notifications ✅
**File:** `backend/app/services/notification_service.py`
- Pluggable notifier: `log` (default) or `webhook` (`NOTIFICATION_BACKEND`,
  `NOTIFICATION_WEBHOOK_URL` for Slack/Teams)
- `notify_pending_approval`, `notify_submitted`, `notify_rejected`
- Failures swallowed — a notification outage never blocks the workflow
- Wired into `transition_application` for Matched / Applied / Rejected

### 7.5 Application API ✅
**File:** `backend/app/api/v1/applications.py`
- `POST /api/v1/applications` — create (Discovered)
- `GET /api/v1/applications` — list (filter: status)
- `GET /api/v1/applications/{id}` — fetch one
- `GET /api/v1/applications/{id}/events` — audit-log history
- `POST /api/v1/applications/{id}/transition` — guarded transition

**Error mapping:** 404 not found, 409 invalid transition/exists, 422 guard failed

**Schemas:** `backend/app/schemas/application.py`

### 7.6 Tests ✅
**File:** `tests/unit/test_application_service.py` - 15 tests (all pass)
- Transition table
- Creation + duplicate rejection + get-or-create idempotency
- Full happy path (Discovered→Matched→Approved→Applied)
- Guards: invalid transition, approve needs resume, apply needs idempotency key,
  apply needs resume still present
- Idempotent submission replay (no duplicate event)
- Reject terminal state, list/filter, ownership isolation, submission failure audit

**Full unit suite:** 214 passed

---

## New Files Created in Phase 7

```
backend/
├── app/
│   ├── models/
│   │   └── job.py                      # Extended ApplicationStatus + ApplicationEvent
│   ├── schemas/
│   │   └── application.py              # Workflow API schemas (NEW)
│   ├── services/
│   │   ├── application_service.py      # State machine + audit log (NEW)
│   │   └── notification_service.py     # Approval/submission notifications (NEW)
│   └── api/v1/
│       └── applications.py             # /applications endpoints (NEW)
├── alembic/versions/
│   └── c7d4e1a9f2b8_add_application_workflow.py  # Migration (NEW)
tests/unit/
└── test_application_service.py         # 15 tests (NEW)
```

---

## Requirements Added (Phase 0-7)

```txt
slowapi==0.1.10          # Rate limiting
structlog==24.1.0        # Structured logging
prometheus-client==0.20.0 # Prometheus metrics
pgvector==0.5.0          # Vector columns
aiosqlite==0.22.1        # SQLite async for tests
email-validator==2.3.0   # Pydantic email validation
playwright==1.63.0       # Browser automation
httpx==0.27.2            # HTTP client (Apify/OpenAI/Cohere/webhooks)
celery==5.6.3            # Task queue
```

Optional:
```txt
boto3                    # S3-compatible document storage
```

---

## Phase 8: Browser Automation - COMPLETED ✅

### 8.1 ATS Selector Configuration ✅
**File:** `backend/app/agents/ats_config.py`
- `ATSConfig` dataclass with ordered fallback selectors per field
- Dedicated configs: **Greenhouse**, **Lever**, **Workday** + **generic** fallback
- `resolve_ats(url)` matches by host; `host_of(url)` helper
- Adding a new ATS = adding data, not code

### 8.2 Application Bot ✅
**File:** `backend/app/agents/application_bot.py`
- `ApplicantData`, `SubmissionRequest`, `SubmissionResult` dataclasses
- `ApplicationFormFiller` protocol (injectable for tests)
- `PlaywrightFormFiller` — real implementation, lazy Playwright import
  - Fills text fields via ordered selector fallbacks
  - Uploads resume/cover letter files
  - Captures full-page screenshot evidence
  - **`dry_run` defaults to True** — never clicks submit unless told to
  - Detects form-ready, submits via submit-button selectors

### 8.3 Politeness Controls ✅
**File:** `backend/app/agents/politeness.py`
- `DomainRateLimiter` — async, per-host minimum interval (default 5s)
- `is_allowed_by_robots(url)` — honours robots.txt disallow rules
  - Fails *open* on network error, but disallow rules always enforced
  - Cached per host root

### 8.4 Orchestration Service ✅
**File:** `backend/app/services/browser_automation_service.py`
- `build_applicant_data()` — public KB profile → `ApplicantData`
  - Materialises approved resume/cover-letter docs to local files for upload
- `submit_application()` — full flow with guards:
  - Rejected application → blocked
  - Real submission requires **Approved** status + approved resume document
  - robots.txt check + domain rate limit
  - Dry-run default; success advances application to **Applied** (idempotent)
  - Failure records `last_error` + audit event without state change
  - **Idempotent replay**: retried task on already-Applied app is a no-op success

### 8.5 Celery Tasks ✅
**File:** `backend/app/tasks/applications.py`
- `submit_application_task(user_id, application_id)` — real submission
  (retry: 3x exponential backoff, max 30 min)
- `dry_run_submission_task(...)` — safe pre-fill inspection

### 8.6 Submission API ✅
**Endpoint:** `POST /api/v1/applications/{id}/submit`
- Body: `{ "dry_run": true }` (default true)
- Returns `ApplicationSubmitResponse` (success, ats, fields_filled,
  evidence_paths, error, application_status)
- Error mapping: 404 not found, 422 blocked/guard-failed

### 8.7 Human-Gated Safety ✅
- **Dry-run by default** — pre-fills and captures evidence without submitting
- Real submission gated on **Approved** application + approved resume
- robots.txt + rate limiting before any navigation
- Evidence screenshots retained for audit
- Only public candidate data is used

### 8.8 Tests ✅
**File:** `tests/unit/test_browser_automation.py` - 12 tests (all pass, no browser)
- ATS resolution + host parsing
- Rate limiter interval enforcement
- robots.txt disallow blocks submission
- Applicant data materialisation from approved docs
- Dry-run from Matched (status unchanged, filler invoked)
- Real submit requires Approved; rejected blocked
- Real success advances to Applied (+ audit event meta)
- Real failure records error, state unchanged
- Idempotent resubmit is a no-op (no duplicate event)
- ATS + applicant data flow into the request

**Full unit suite:** 226 passed

---

## New Files Created in Phase 8

```
backend/
├── app/
│   ├── agents/
│   │   ├── ats_config.py               # ATS selector maps (NEW)
│   │   ├── politeness.py               # Rate limiter + robots.txt (NEW)
│   │   └── application_bot.py          # Playwright form filler (NEW)
│   ├── services/
│   │   └── browser_automation_service.py  # Orchestration + guards (NEW)
│   ├── tasks/
│   │   └── applications.py             # Submission Celery tasks (NEW)
│   └── api/v1/
│       └── applications.py             # + /submit endpoint
tests/unit/
└── test_browser_automation.py          # 12 tests (NEW)
```

---

## Requirements Added (Phase 0-8)

```txt
slowapi==0.1.10          # Rate limiting
structlog==24.1.0        # Structured logging
prometheus-client==0.20.0 # Prometheus metrics
pgvector==0.5.0          # Vector columns
aiosqlite==0.22.1        # SQLite async for tests
email-validator==2.3.0   # Pydantic email validation
playwright==1.47.0       # Browser automation
httpx==0.27.2            # HTTP client (Apify/OpenAI/Cohere/webhooks/robots)
celery==5.4.0            # Task queue
```

Optional:
```txt
boto3                    # S3-compatible document storage
```

---

## Phase 9: Dashboard (Frontend) - COMPLETED ✅

### 9.1 Design System ✅
**File:** `frontend/src/app/globals.css`
- Tailwind v4 `@theme` tokens for the exact requested palette:
  Primary `#2563EB` / hover `#1D4ED8`, Secondary `#64748B`,
  Background `#F8FAFC`, Card `#FFFFFF`, Border `#E2E8F0`,
  Text `#0F172A`, Muted `#64748B`, Success `#059669`,
  Warning `#D97706`, Danger `#DC2626`.
- Consumed via utilities (`bg-primary`, `text-muted`, `border-border`, …)

### 9.2 API Client + Auth ✅
**Files:** `frontend/src/lib/api.ts`, `types.ts`, `auth.tsx`
- `apiFetch` wrapper: bearer token, typed errors, 401 auto-logout
- Full typed clients: auth, jobs, evaluation, search, kb, documents, applications
- `AuthProvider` / `useAuth` context (login, register, logout, refresh)

### 9.3 App Shell ✅
**Files:** `frontend/src/app/(app)/layout.tsx`, `components/Sidebar.tsx`, `TopBar.tsx`, `icons.tsx`
- Protected route group; redirects unauthenticated users to `/login`
- Sidebar nav + user footer, sticky top bar with agent status

### 9.4 Pages ✅
- **`/login`, `/register`** — auth flows with validation
- **`/dashboard`** — stat cards (jobs, applications, applied, avg match),
  recent discoveries, pipeline breakdown, top matches
- **`/jobs`** — browse + hybrid/semantic search + on-demand fit evaluation
  (score ring, priority/recommendation, matched/partial/missing skills,
  gaps, technical match)
- **`/profile`** — Candidate KB editor (identity, target roles, education,
  work authorization) + advanced JSON for skills/claims/experience, with
  server-side validate & versioned save
- **`/documents`** — generate resume/cover letter per job, review/edit,
  approve/reject/regenerate, ATS score + matched keywords
- **`/applications`** — kanban pipeline across all stages, advance/reject,
  **dry-run** and **real submit** with confirmation, failure surfacing

### 9.5 Build & Verification ✅
- `tsc --noEmit` → clean
- `next build` (Next 16 / Turbopack) → **8 routes** compiled successfully:
  `/`, `/login`, `/register`, `/dashboard`, `/jobs`, `/profile`,
  `/documents`, `/applications`
- `eslint src` → **0 errors**, 4 warnings (data-fetching effect rule,
  documented & downgraded in `eslint.config.mjs`)

### 9.6 Config ✅
- `frontend/.env.local.example` — `NEXT_PUBLIC_API_URL`
- `frontend/README.md` — setup, features, palette table, structure

---

## New/Changed Files in Phase 9

```
frontend/
├── .env.local.example                      # API base URL (NEW)
├── README.md                               # Rewritten (NEW)
├── eslint.config.mjs                       # Rule override (MODIFIED)
└── src/
    ├── app/
    │   ├── globals.css                     # Palette tokens (REWRITTEN)
    │   ├── layout.tsx                      # AuthProvider root (REWRITTEN)
    │   ├── page.tsx                        # Auth-based redirect (REWRITTEN)
    │   ├── login/page.tsx                  # (NEW)
    │   ├── register/page.tsx               # (NEW)
    │   └── (app)/
    │       ├── layout.tsx                  # Protected shell (NEW)
    │       ├── dashboard/page.tsx          # (NEW)
    │       ├── jobs/page.tsx               # (NEW)
    │       ├── profile/page.tsx            # (NEW)
    │       ├── documents/page.tsx          # (NEW)
    │       └── applications/page.tsx       # (NEW)
    ├── components/
    │   ├── ui.tsx                          # Card/Button/Badge/... (NEW)
    │   ├── Sidebar.tsx                     # (NEW)
    │   ├── TopBar.tsx                      # (NEW)
    │   └── icons.tsx                       # (NEW)
    └── lib/
        ├── api.ts                          # Typed API client (NEW)
        ├── types.ts                        # API types (NEW)
        └── auth.tsx                        # Auth context (NEW)
```

---

## Phase 9B: Agent Experience / Product Differentiation - COMPLETED ✅

**Goal:** make the existing intelligence visible and agentic — no new backend
capability. Success criterion: a new user understands within 30 seconds that
JobAgent is an AI career agent, not a job board.

### 9B.1 Agent Command Center ✅ (rebuilt `/dashboard`)
- Agent hero with live presence ("the agent is scanning your pipeline…")
- Daily summary: discovered today, strong-fit roles, awaiting review, ready to submit
- Action Center, top recommendations, agent activity, pipeline breakdown

### 9B.2 Intelligent Opportunity Feed ✅ (`/opportunities`)
- Buckets: **Recommended / Worth reviewing / Low fit / All**
- Ranked by actual fit (deterministic client-side pre-score of candidate skills
  vs. required/preferred skills, alias-aware; falls back to description inference)
- Per-role: fit ring, "why you" matched chips, gaps; Analyze / Track / Posting

### 9B.3 Explainable Job Intelligence ✅
- `MatchBreakdown`: fit ring + priority/recommendation, match-signal bars
  (Technical, Role, Eligibility, Evidence), **Why you / Gaps / Risks**

### 9B.4 Agent Activity Timeline ✅ (`/activity`)
- Discovery → Matching → Documents → Approval → Application, built from **real**
  timestamps and application audit events (nothing simulated)
- Stage filters + counts

### 9B.5 AI Application Copilot ✅ (`/copilot`)
- Guided stepper: Choose → Analyze → Resume → Cover letter → Review & apply
- One workflow instead of separate CRUD screens; inline document previews

### 9B.6 Human-in-the-Loop ✅
- The agent recommends; the user approves/edits/rejects
- Submission requires an approved resume + application approval; dry-run first
- Copilot checklist makes the gate explicit; **never silently submits**

### 9B.7 Smart Document Workspace ✅ (rebuilt `/documents`)
- Tabs: Preview · **Why this doc** · Versions
- Shows ATS score, matched/missing requirements, evidence used (claim IDs),
  and full version history

### 9B.8 Action Center ✅
- Prioritized "what needs you next": documents awaiting review, applications
  ready to submit, matches needing approval, recommended opportunities

### 9B.9 Natural-Language Career Assistant ✅
- `IntentComposer` on Opportunities: e.g. *"AI Engineer roles in UAE with strong
  Python/LLM fit"*
- `parseIntent` extracts roles, locations, work mode, skills → search + rank,
  and shows an **"Understood:"** chip summary

### 9B.10 Product Identity ✅
- Agentic navigation (Command Center, Opportunities, Copilot, Document
  Workspace, Applications, Agent Activity, Candidate Profile)
- Reasoning-first layouts, agent presence, fit rings, timelines

### 9B.11 Supporting changes ✅
- **Backend (surface existing data only):** `JobPostingRead`/`JobPostingCreate`
  now expose already-stored extended fields (skills, work_mode, application_url,
  etc.); `job_service.create_job` persists them. Embedding still internal.
- **Agent lib:** `lib/agent.ts` (skill matching, pre-scoring, intent parsing,
  action derivation, timeline), `lib/useAgentData.ts` (shared loader)
- **Components:** `components/agent.tsx` (AgentAvatar, FitRing, MatchBreakdown,
  ActionCenter, ActivityTimeline, IntentComposer, Stepper)

### 9B.12 Verification ✅
- `tsc --noEmit` → clean
- `next build` → **10 routes** (`/dashboard`, `/opportunities`, `/copilot`,
  `/documents`, `/applications`, `/activity`, `/profile`, `/login`,
  `/register`, `/`)
- `eslint src` → **0 errors** (7 documented warnings)
- Backend suite → **226 passed**

### 9B.13 Bug fix: Candidate KB save shape (canonical serialization) ✅
**Problem:** the Profile editor emitted `skills`/`claims` as bare arrays (should
be mappings), and later emitted bare *strings* (`"Python"`, `"RAG"`) where the
backend expects full record objects (`SkillRecord`, `ClaimRecord`,
`WorkExperienceRecord`, `ProjectRecord`). `PUT /api/v1/profile/kb` returned 422.

**Fix:** pure module `frontend/src/lib/kb.ts`:
- `canonicalizeSkills/Claims/Experience/Preferences`:
  - wrap bare arrays in the correct mapping,
  - **coerce bare strings into the exact record schema** (with unique
    `SKILL-AUTO-n` / `CLAIM-AUTO-n` / `EXP-AUTO-n` / `PROJ-AUTO-n` ids that
    avoid collisions with user ids, `verified: false`,
    `disclosure: "undetermined"`, empty reference lists),
  - preserve already-canonical record objects unchanged.
- `buildCandidateKB(profile, advanced)` → canonical KB for save
- `serializeAdvanced(kb)` → canonical JSON for the editor
- Profile `onSave` resyncs the editor from the validated response, so coerced
  strings visibly become records.

**Regression tests:**
- Frontend: `frontend/tests/kb.test.mjs` (**20 tests**, `npm test` →
  `node --test`): mapping wrapping, **string → record coercion** (skills,
  claims, experience, projects), id-collision avoidance, duplicate-string
  uniqueness, canonical-object preservation (reference identity), profile
  coercion, full round trip.
- Backend: 7 new tests in `tests/unit/test_candidate_kb_service.py`, including
  one that validates the **exact frontend-coerced record shapes** and asserts
  bare-array collections are rejected.

**Result:** backend **233 passed**; frontend `node --test` 20 passed;
`next build` clean; `eslint` 0 errors.

### 9B.14 Candidate Profile rebuilt as a structured profile builder ✅
**Goal:** a polished career-product profile builder — the Advanced JSON editor
is gone; users never touch JSON.

**Mapping layer** (`frontend/src/lib/kb.ts`, backend schema unchanged):
- New `ProfileForm` model + `formToCandidateKB()` / `candidateKBToForm()`:
  - **Skills** — names → `SkillRecord` objects
  - **Claims** — text + related skills → `ClaimRecord` (title derived from text)
  - **Experience** — cards → `WorkExperienceRecord`; the free-text description
    is stored as a linked `EXP-CLAIM-<id>` claim and reconstructed on load
  - **Projects** — cards → `ProjectRecord` (`skills_used`, `verification_source`)
  - **Preferences** — work modes, locations, relocation, visa, compensation,
    exclusions → `CandidatePreferences` + `work_authorization`
  - **Target roles** — approved taxonomy persisted; custom roles shown
    (local-only, clearly labelled)
  - Legacy migration: bare-string skills/claims and old shapes are recovered
- `validateProfileForm()` — inline validation (name, email, roles, numbers)

**UI** (`frontend/src/app/(app)/profile/page.tsx` + `components/forms.tsx`):
- 7 sections: Identity & Education · Target Roles · Skills · Work Experience ·
  Projects · Claims & Achievements · Work Preferences
- Reusable `ChipInput` (type + Enter, removable chips), `Section`, `RepeatCard`
- Add/remove controls, inline errors, prominent Save/Validate, clear
  "Saved as version X" state, responsive, existing blue/slate system

**Tests:** `frontend/tests/kb.test.mjs` → **31 tests** (added: skills/claims/
experience/projects/preferences serialization, form↔KB round trip,
load→edit→save→load, legacy migration, validation).

**Result:** backend **233 passed**; frontend **31 passed**; `tsc` clean;
`next build` clean; `eslint` 0 errors.

---

## New/Changed Files in Phase 9B

```
frontend/src/
├── lib/
│   ├── agent.ts                          # Intelligence helpers (NEW)
│   └── useAgentData.ts                   # Shared data + derived state (NEW)
├── components/
│   ├── agent.tsx                         # Agent UI kit (NEW)
│   └── icons.tsx                         # + Activity, Copilot (MODIFIED)
├── app/(app)/
│   ├── dashboard/page.tsx                # Command Center (REBUILT)
│   ├── opportunities/page.tsx            # Intelligent feed + NL (NEW)
│   ├── copilot/page.tsx                  # Guided workflow (NEW)
│   ├── activity/page.tsx                 # Activity timeline (NEW)
│   ├── documents/page.tsx                # Document Workspace (REBUILT)
│   └── jobs/                             # REMOVED (replaced by opportunities)
backend/app/
├── schemas/job.py                        # Surface extended fields (MODIFIED)
└── services/job_service.py               # Persist extended fields (MODIFIED)
```

---

## Next Steps: Phase 10 - Production Readiness

### 10.1 Kubernetes Hardening
- HPA, PodDisruptionBudgets, NetworkPolicies
- Sealed/External Secrets for `SECRET_KEY`, DB, API keys
- Frontend deployment + ingress

### 10.2 Observability
- Prometheus scrape config + Grafana dashboards
- Loki log aggregation; OpenTelemetry tracing

### 10.3 Reliability
- Backups / restore runbook (RPO/RTO)
- Load testing + capacity planning
- Alerting rules

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