# Architecture Decisions & Tradeoffs

## 1. Canonical JobPosting

**Decision:** use JobPosting as the active application representation.

**Tradeoff:** a legacy jobs model remains for old fixtures, but adapters are kept
out of the active discovery -> evaluation path.

**Why:** one schema boundary reduces silent field drift and makes evaluation,
search and documents reproducible.

## 2. Hybrid ranking instead of embedding-only ranking

**Decision:** combine semantic similarity with deterministic technical, role,
experience, education, preference and evidence features.

**Tradeoff:** more code and calibration work, but ranking becomes explainable and
hard eligibility constraints cannot be hidden by semantic similarity.

## 3. 1536-dimension embedding contract

**Decision:** OpenAI text-embedding-3-small / 1536 dimensions for v1.

**Tradeoff:** provider lock-in versus a stable pgvector contract. Changing the
model requires regeneration rather than mixing dimensions.

## 4. Human-gated browser submission

**Decision:** dry-run by default; real submission requires explicit approval.

**Tradeoff:** less automation throughput, substantially lower accidental
submission risk.

## 5. Offline learning loop

**Decision:** analyze application outcomes offline before changing ranking.

**Tradeoff:** slower adaptation, but avoids feedback loops, selection bias and
silent ranking drift.

## 6. Service-level E2E plus controlled ATS E2E

**Decision:** keep the core pipeline deterministic and use a mock ATS for safe
submission assertions.

**Tradeoff:** it does not prove universal ATS reliability; live ATS evidence is
maintained as a separate release gate.
