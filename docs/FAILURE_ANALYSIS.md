# Failure Analysis

These are engineering failures discovered during implementation, not invented
failure stories.

## F1 — Evaluator syntax regression

**Symptom:** Pipeline Validation failed during Python import/collection.

**Cause:** incremental scoring edits left missing commas in the EvaluationResult
constructor.

**Detection:** GitHub Actions failed before tests executed.

**Fix:** corrected the malformed constructor and added compileall to the main CI
gate.

**Prevention:** keep syntax/compile checks before expensive integration jobs.

## F2 — Real ATS validator import-path failure

**Symptom:** the live dry-run workflow initially failed with ModuleNotFoundError
for the backend app package.

**Cause:** the script depended on workflow-level PYTHONPATH rather than deriving
the repository backend path itself.

**Prevention:** validator should establish its import root from its own file path;
CI configuration must not be the only source of package discoverability.

## F3 — Placeholder JD persistence

**Symptom:** some discovery paths previously persisted "Pending extraction...".

**Cause:** listing discovery and detail-page extraction were treated as one
operation without a hard persistence boundary.

**Fix:** detail extraction now runs before persistence and failed extraction is
skipped.

**Lesson:** external scraping is a two-stage pipeline: discovery evidence first,
verified detail evidence second.

## F4 — Embedding dimension drift risk

**Symptom:** providers exposed multiple dimensions while pgvector was fixed.

**Risk:** incompatible vectors can corrupt a search index or fail at query time.

**Fix:** v1 contract is locked to 1536 dimensions with startup and write-time
validation.

## F5 — Provisional rather than human-gold ranking data

**Symptom:** the repository lacked enough real persisted jobs for a legitimate
human-verified benchmark.

**Decision:** publish a clearly labelled provisional 50-query benchmark rather
than misrepresent synthetic labels as gold truth.

**Lesson:** evaluation provenance is more valuable than a misleading metric.
