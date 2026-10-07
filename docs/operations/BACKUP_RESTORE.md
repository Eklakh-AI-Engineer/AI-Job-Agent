# Backup / Restore Verification

## Supabase PostgreSQL
Use the production Supabase project backup/PITR facilities and verify a restore into a disposable environment. Validate schema/migrations, users and candidate KB records, job_postings, application statuses/events, indexes and pgvector, and row counts before/after restore.

## Artifact storage
Verify a representative generated PDF/DOCX artifact can be restored from the configured S3-compatible bucket.

## Acceptance
A backup is not considered verified merely because backups are enabled. Record the restore timestamp, source backup identifier, restored environment, row-count comparison, and application smoke result.

This repository currently cannot truthfully claim a production restore test because the AI-Job-Agent Supabase project is not connected to the current ChatGPT integration.
