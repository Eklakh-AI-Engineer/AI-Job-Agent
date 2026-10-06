# Ranking Evaluation Dataset

## v1 benchmark fixture

`benchmark_job_ranking_v1.jsonl` contains **50 query groups × 5 candidate jobs = 250 labelled pairs**.

Each group records:
- a user-style search query;
- five candidate job archetypes;
- ordinal relevance labels (`0`–`3`);
- relevant-job IDs;
- difficult-negative IDs where present;
- provenance and review-state metadata.

The benchmark is intentionally marked `benchmark-fixture` and `human_verified: false`. The labels are machine-generated from the declared fixture archetypes. This avoids presenting synthetic labels as human evidence.

## Promotion to human-gold

To promote this fixture to a true human-gold release benchmark:
1. replace synthetic job IDs with real persisted/discovered jobs;
2. have a human reviewer label relevance independently;
3. record matched/missing skills and eligibility outcomes;
4. record reviewer rationale for difficult cases;
5. adjudicate disagreements;
6. freeze the dataset and SHA-256;
7. evaluate the calibrated ranker on the frozen labels.

The metric runner already supports the grouped format, so promotion does not require changing the scoring engine.

## Regression

`ranking_regression_thresholds_v1.json` defines the CI floor. The frozen prediction file is a contract/regression baseline, not a production-quality claim.

## Calibration

`backend/evaluation/calibration.py` implements a dependency-free sigmoid score calibrator. It maps raw 0–100 ranking scores to an estimated relevance probability while preserving ordering. Coefficients must be fitted from independent labelled data before being treated as empirical calibration.
