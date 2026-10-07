# Human Label Adjudication & Benchmark Freeze Candidate v1

**Source workbook:** `docs/evaluation/Human_Benchmark_Labeled_v1.xlsx`  
**Source SHA-256:** `3723436be0cd843e57edf569a3661c551960f225ea7587ac1a71369909f9c5bc`  
**Generated from CI run:** `37646085225`  
**Commit audited:** `833fc942f3faeeb72cd2f5bab44e2034be3aca26`

## 1. Label verification

Automated integrity checks passed:

- 500/500 rows parsed successfully.
- Human labels are restricted to the canonical ordinal set 0–3.
- Human scores are numeric and bounded to 0–100.
- No malformed human-label rows were detected.
- Label distribution:
  - 0: 133
  - 1: 90
  - 2: 227
  - 3: 50

### Independent adjudication status

**NOT COMPLETED.**

The repository does not contain an independent second-reviewer/adjudicator record. The evaluator therefore does not promote the existing human labels to “human-gold”.

The current run reports:

- AI/human exact agreement: 21.20%
- Disagreements: 394/500
- ±1 label agreement: 100%
- Cohen's kappa: -0.0862
- Quadratic weighted kappa: 0.4260

The 394 disagreements are preserved for human adjudication. They must not be auto-corrected from the AI prediction.

## 2. Real persisted-job mapping

**NOT COMPLETED.**

The workbook contains only synthetic benchmark identifiers. There are 100 unique job IDs in the 500 rows, following the `JOB-001` … `JOB-100` pattern.

No repository evidence currently proves that these IDs correspond to rows in the production `job_postings` persistence layer.

Therefore:

- `real_persisted_jobs = false`
- No synthetic ID has been promoted to a production job ID.
- No label has been rewritten to force a database match.

## 3. Candidate freeze

The source workbook has an immutable content hash recorded above.

This is a **candidate freeze**, not a golden-benchmark freeze.

The benchmark may be reproduced exactly from the source workbook hash, but it is not promoted until:

1. A second human independently reviews/adjudicates the 394 disagreement cases.
2. Adjudication decisions and rationales are recorded.
3. Every benchmark job maps to a real persisted/discovered job record.
4. Canonical query grouping is established.
5. The adjudicated dataset is frozen and receives a new SHA-256.
6. The promotion evaluator is run with both `--promote` and `--real-persisted-jobs`.

## 4. Promotion status

```yaml
status: candidate_freeze
human_verified: false
independent_adjudication: false
real_persisted_jobs: false
frozen: false
source_hash_recorded: true
production_ranking_baseline: false
```

**Decision:** keep `golden_job_ranking_v1` provisional. Do not enable production ranking claims from this dataset.
