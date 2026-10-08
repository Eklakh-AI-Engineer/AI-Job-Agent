# Human Gold Freeze Manifest — v1

**Benchmark:** golden_job_ranking_v1  
**Status:** Frozen + human verified (synthetic)  
**Rows:** 500  
**Unique jobs:** 100  
**Candidates/job:** 5

## Adjudication completion

- Reviewer 2: 141/141 disputed cases
- Two-reviewer consensus: 83/141
- Third adjudication: 58/58
- Final gold: 500/500 resolved
- Independent adjudication: complete

## Final agreement

- Initial human/reference: 359/500 (71.8%)
- Final gold/reference: 397/500 (79.4%)

## Final label distribution

- No Match: 120
- Borderline: 111
- Weak Match: 214
- Match: 25
- Strong Match: 30

## Frozen benchmark metrics

- Precision@5: 0.7600
- Recall@5: 1.0000
- nDCG@5: 0.9105
- MRR: 1.0000

## Artifact hashes

- Source workbook SHA-256: 908597ca7e9a995fe83f0fc98d8ae608561543f6f71bdf51eed0cb7408a6ee92
- Final workbook SHA-256: ce65bdb07b9724b9851ac91da578a5bce86a0d01715b226cd2ebecd0d737273e

## Promotion boundary

This benchmark is **not yet the production-authoritative ranking baseline**. JOB-001..JOB-100 are synthetic and have not been proven to map to real persisted/discovered jobs. Production promotion remains blocked until that mapping is completed.
