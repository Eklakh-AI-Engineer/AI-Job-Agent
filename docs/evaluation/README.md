# Ranking Evaluation

## Benchmark lifecycle

golden_job_ranking_v1 is now a **frozen, human-verified synthetic benchmark**.

### Human adjudication status
- 500 candidate rows
- 100 unique JOB-* groups
- 5 candidates per group
- Initial human/reference exact agreement: **359/500 (71.8%)**
- Initial disagreements: **141**
- Independent Reviewer 2 completed: **141/141**
- Two-reviewer consensus: **83**
- Third adjudication completed: **58/58**
- Final gold/reference exact agreement: **397/500 (79.4%)**
- Final gold SHA-256: `ce65bdb07b9724b9851ac91da578a5bce86a0d01715b226cd2ebecd0d737273e`

### Frozen human-gold baseline
Using the workbook Match Score as the ranking signal:

| Metric | Frozen result |
|---|---:|
| precision@5 | 0.5380 |
| recall@5 | 1.0000 |
| nDCG@5 | 0.9105 |
| MRR | 0.7858 |

These are **frozen synthetic benchmark metrics**, not production performance claims.

### Required production promotion
1. Map synthetic job IDs to real persisted/discovered jobs.
2. Preserve the adjudicated labels while replacing synthetic references with auditable persisted-job references.
3. Generate the production-authoritative baseline from the actual runtime ranker.
4. Point ranking_regression_gate.py at that authoritative baseline.
5. Run the complete backend/E2E regression suite.

See benchmark_status.json for machine-readable lifecycle state.

## Regression gate
The repository contains scripts/evaluate_ranking.py for benchmark metrics and scripts/ranking_regression_gate.py for baseline comparison.
The regression gate is enabled against the frozen human-gold reference artifacts. It is **not yet a production-quality gate** because the benchmark job IDs are synthetic.

Required metrics: precision_at_5, recall_at_5, ndcg_at_5, and mrr.


## Production promotion contract (2026-10-09)

The committed `baseline.json` and `latest.json` are frozen synthetic/reference metrics. They are not production-authoritative ranking results.

- `scripts/ranking_regression_gate.py` rejects non-authoritative inputs by default.
- `.github/workflows/ci.yml` uses `--allow-non-production-baseline` only for synthetic/reference plumbing; its green status is not a production ranking pass.
- `.github/workflows/production-ranking-regression.yml` is the manual release gate. It must pass against files marked `production_authoritative: true` and the same frozen dataset hash and `ranking_version`.
- `scripts/validate_job_mapping.py` validates a mapping CSV against every unique benchmark Job ID. It emits a manifest marked `production_authoritative: false` because schema validation alone cannot authenticate the source database.
- Template: `docs/evaluation/real_job_mapping_template.csv`.

Before promotion, export the production `job_postings` records, review each mapping, record the source-export SHA-256, generate runtime-ranker metrics over the mapped benchmark, and preserve the run output. Do not set `production_authoritative: true` based solely on a hand-edited JSON flag.
