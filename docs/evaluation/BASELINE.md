# Ranking baseline v1

The repository now has a **frozen human-gold benchmark baseline**. The baseline is deliberately marked non-production because the 100 JOB-* identifiers are still synthetic.

| Metric | Baseline | Latest |
|---|---:|---:|
| Precision@5 | 0.5380 | 0.5380 |
| Recall@5 | 1.0000 | 1.0000 |
| nDCG@5 | 0.9105 | 0.9105 |
| MRR | 0.7858 | 0.7858 |

## Provenance
- Benchmark: golden_job_ranking_v1
- Rows: 500
- Query groups: 100
- Candidates/group: 5
- Final gold workbook SHA-256: ce65bdb07b9724b9851ac91da578a5bce86a0d01715b226cd2ebecd0d737273e
- Ranking signal: workbook Match Score
- Status: frozen + independently adjudicated
- Production authoritative: **false**

These metrics replace the old fixture-order 1.0000 infrastructure baseline. The old baseline was not meaningful as ranking-quality evidence because the fixture candidate order was already aligned with provisional relevance labels.

## Release boundary
The regression-gate plumbing is now anchored to the frozen human-gold benchmark. The remaining production-promotion blocker is **real persisted/discovered-job mapping**. Once real job IDs and auditable references replace the synthetic JOB-* IDs, regenerate the baseline from the actual runtime ranker and flip the production-authoritative flag.

Do not describe the current numbers as production ranking performance.
