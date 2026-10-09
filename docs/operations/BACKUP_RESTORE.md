# Backup / Restore Verification

## Supabase PostgreSQL
Use the production Supabase project backup/PITR facilities and verify a restore into a disposable environment. Validate schema/migrations, users and candidate KB records, job_postings, application statuses/events, indexes and pgvector, and row counts before/after restore.

## Artifact storage
Verify a representative generated PDF/DOCX artifact can be restored from the configured S3-compatible bucket.

## Acceptance
A backup is not considered verified merely because backups are enabled. Record the restore timestamp, source backup identifier, restored environment, row-count comparison, and application smoke result.

This repository currently cannot truthfully claim a production restore test because the AI-Job-Agent Supabase project is not connected to the current ChatGPT integration.


## Audit result — 2026-10-09

**Status: NOT VERIFIED.** The live API health endpoint reported `database=healthy`, but that proves connectivity, not recoverability. No restore was executed because this session does not have authorized access to the AI Job Agent Supabase project or a separate disposable restore target.

Before running the restore test:

1. Confirm access to the correct AI Job Agent Supabase project (not another project's database).
2. Create or select a separate disposable PostgreSQL target. Confirm its project/host is not production.
3. Capture a source backup/PITR identifier and timestamp.
4. Restore schema and data into the disposable target; verify migrations, `job_postings`, `application_statuses`, user-owned candidate KB records, pgvector extension/indexes, and row counts.
5. Run the backend smoke suite against the restored target.
6. Restore representative generated PDF/DOCX objects from the configured storage bucket and verify checksums.
7. Record only sanitized evidence: project aliases, backup identifier, timestamps, counts, migration result, object checksums, and smoke results. Never upload a raw database dump or secrets as a workflow artifact.

Do not mark this gate passed until both database and artifact-storage restore paths have been exercised successfully.
