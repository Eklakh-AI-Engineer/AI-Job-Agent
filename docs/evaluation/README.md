# Ranking Evaluation Dataset

## v1 provisional benchmark

`golden_job_ranking_v1.jsonl` contains **50 query groups × 5 candidate jobs**.

Each group contains:
- `query_id`
- user-style job-search query
- candidate job IDs
- ordinal relevance labels (`0`–`3`)
- provenance/status fields

### Provenance rule

The current repository does not contain 50 real persisted production jobs. The benchmark therefore uses the existing synthetic candidate fixture and synthetic job archetypes as a **provisional evaluation scaffold**.

It is **not yet human-verified** and must not be presented as measured production quality.

### Promotion to golden

Before calling this dataset a true golden benchmark:
1. replace synthetic job IDs with jobs from the actual persisted/discovered corpus;
2. have a human reviewer label relevance independently;
3. record reviewer rationale for difficult cases;
4. adjudicate disagreements;
5. freeze the resulting dataset with a version/hash;
6. keep difficult negatives such as keyword-overlap false positives and semantically similar but ineligible roles.

The evaluation runner in the next milestone consumes the same grouped format, so the provisional dataset can be replaced without changing metric code.
