# Human Label Adjudication & Benchmark Freeze Status v3

**Source workbook:** `docs/evaluation/Human_Benchmark_Labeled_v1.xlsx`  
**Source workbook SHA-256:** `908597ca7e9a995fe83f0fc98d8ae608561543f6f71bdf51eed0cb7408a6ee92`  
**Final frozen adjudication artifact SHA-256:** `ce65bdb07b9724b9851ac91da578a5bce86a0d01715b226cd2ebecd0d737273e`  
**Rows:** 500  
** **Ranking groups:** 100 synthetic jobs × 5 candidates

## Adjudication completed

The original workbook contained one human annotation pass across all 500 candidates.

- Initial exact agreement with reference labels: **359/500 (71.8%)**
- Initial disagreements: **141**
- Reviewer 2 completed all **141** disputed cases.
- Two-reviewer consensus: **83/141 (58.9%)**
- Remaining disagreements: **58**
- A third adjudicator resolved all **58/58** remaining cases.
- Therefore all 500 benchmark rows now have a resolved final-gold label.

The five-level ordinal rubric is:

- 0 = No Match
- 1 = Borderline
- 2 = Weak Match
- 3 = Match
- 4 = Strong Match

## Final human-gold distribution

| Final Gold Label | Count |
|---|---:|
| No Match | 120 |
| Borderline | 111 |
| Weak Match | 214 |
| Match | 25 |
| Strong Match | 30 |

Final gold vs reference exact agreement is **397/500 (79.4%)**.

The workbook's prior Independent Analysis quadratic weighted-kappa value is not used as an authoritative statistic because the repository's standard weighting implementation did not reproduce it. The adjudicated labels are the authoritative human-gold decisions for this frozen synthetic benchmark.

## Freeze decision

**HUMAN-GOLD VERIFIED AND FROZEN.**

The completed adjudication record is preserved in the local reconciliation/final workbook and the machine-readable adjudicated benchmark artifact.

Frozen artifact:

- `Human_Gold_Final_v1.xlsx`
- SHA-256: `ce65bdb07b9724b9851ac91da578a5bce86a0d01715b226cd2ebecd0d737273e`
- Local machine-readable artifact produced with the freeze: `golden_job_ranking_v1_final.jsonl`

## Production promotion status

**NOT YET PRODUCTION-AUTHORITATIVE.**

The 100 benchmark job IDs remain synthetic (`JOB-001` ... `JOB-100`). There is currently no evidence that they map one-to-one to persisted production `job_postings` records.

Therefore:

1. Human-gold verification is complete.
2. Benchmark freeze is complete.
3. Production ranking baseline generation is still blocked on real persisted-job mapping.
4. The regression gate must not be repointed to this synthetic benchmark as the production baseline until that mapping is established.

## Current state

```yaml
status: frozen_adjudicated_synthetic
human_verified: true
independent_adjudication: true
frozen: true
real_persisted_jobs: false
production_ranking_baseline: false
source_hash_recorded: true
final_frozen_hash_recorded: true
```

**Decision:** treat this artifact as the frozen human-gold benchmark. Do not claim production ranking quality until the synthetic-to-persisted job mapping is completed.
