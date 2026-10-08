# Human Label Adjudication & Benchmark Freeze Candidate v2

**Source workbook:** `docs/evaluation/Human_Benchmark_Labeled_v1.xlsx`  
**Uploaded workbook SHA-256:** `908597ca7e9a995fe83f0fc98d8ae608561543f6f71bdf51eed0cb7408a6ee92`  
**Rows:** 500  
**Ranking groups:** 100 synthetic jobs × 5 candidates

## Label verification

The workbook's `Benchmark Data` sheet contains 500 completed independent human annotations. The `Final Chosen Label` column matches the human annotation and is treated as the human annotation output.

The workbook uses a five-level ordinal rubric:

- 0 = No Match
- 1 = Borderline
- 2 = Weak Match
- 3 = Match
- 4 = Strong Match

Reference/AI vs human annotation:

- Exact agreement: **359/500 (71.8%)**
- Disagreements requiring adjudication: **141/500**
- Cohen's kappa: **0.595673**
- Standard quadratic weighted kappa: **0.677025**

The workbook's `Independent Analysis` sheet reports a quadratic weighted kappa of 0.8670. That figure is not reproduced by the repository's standard ordinal weighting implementation and is therefore not used as the authoritative statistic until its weighting methodology is reconciled.

## Ranking-group contract

`Evaluation ID` is row-level (`EVAL-0001` ... `EVAL-0500`) and must not be treated as a ranking query group.

Each `Job ID` contains exactly five candidate rows, so the evaluator now falls back to `Job ID` as the ranking group when no explicit query-group identifier is available.

## Independent adjudication

**NOT COMPLETED.**

The workbook contains one independent annotation pass. There is no second-reviewer/adjudication record for the 141 disagreement cases.

The repository therefore does **not** mark the benchmark as human-gold or production-validated.

## Real persisted-job mapping

**NOT COMPLETED.**

The 100 job identifiers are synthetic `JOB-001` ... `JOB-100`. No repository evidence currently proves that they correspond to production `job_postings` records.

## Freeze / promotion

The uploaded workbook is reproducible by SHA-256, but it is a **candidate human-labeled artifact**, not a production gold freeze.

Promotion remains blocked until:

1. A second human independently reviews/adjudicates all 141 disagreements.
2. Decisions and rationales are recorded.
3. Synthetic IDs are mapped to real persisted/discovered jobs.
4. The adjudicated dataset is frozen with a final SHA-256.
5. The real ranking baseline is generated from that frozen dataset.
6. The regression gate is pointed at that authoritative baseline.

**Current state**

```yaml
status: provisional
human_verified: false
independent_adjudication: false
real_persisted_jobs: false
frozen: false
production_ranking_baseline: false
source_hash_recorded: true
```

**Decision:** retain `golden_job_ranking_v1` as provisional. Do not claim production ranking quality from this benchmark yet.
