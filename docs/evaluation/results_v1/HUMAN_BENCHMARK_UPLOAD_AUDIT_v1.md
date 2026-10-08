# Human Benchmark Upload Audit v1

**Workbook:** `Human_Benchmark_Labeled_v1.xlsx`  
**SHA-256:** `908597ca7e9a995fe83f0fc98d8ae608561543f6f71bdf51eed0cb7408a6ee92`

## Verified

- 500/500 rows parsed from `Benchmark Data`.
- 100 unique synthetic `JOB-*` ranking groups.
- Exactly 5 candidate rows per job.
- Human annotation is populated for all rows.
- `Final Chosen Label` matches the independent `Human Label` output.
- Five-level rubric: No Match=0, Borderline=1, Weak Match=2, Match=3, Strong Match=4.
- Reference/AI vs human exact agreement: 359/500 (71.8%).
- Disagreements requiring second review: 141/500.
- Cohen's kappa: 0.595673.
- Standard quadratic weighted kappa: 0.677025.
- `Evaluation ID` is row-level; ranking groups are `Job ID`.

## Repo fixes applied

- Evaluator now explicitly selects `Benchmark Data`.
- Five-level 0–4 label parsing is supported.
- Ranking evaluation falls back from row-level `EVAL-* ` identifiers to `JOB-*` groups.
- Promotion flags no longer falsely assert human-gold status.
- Benchmark lifecycle metadata and adjudication status were reconciled to the uploaded artifact.

## Still blocked

- Second independent human adjudication of 141 disagreements.
- Mapping synthetic job IDs to real persisted/discovered jobs.
- Final adjudicated freeze and production baseline.
