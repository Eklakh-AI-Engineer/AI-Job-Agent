# Ranking Evaluation

## Benchmark lifecycle

golden_job_ranking_v1.jsonl is currently a **provisional** 50-query × 5-candidate benchmark. It exercises the evaluation machinery but is not evidence of production ranking quality until promoted.

### Required promotion

1. Replace synthetic job IDs with real persisted/discovered jobs.
2. Assign independent human relevance labels.
3. Record rationale/evidence for difficult cases.
4. Adjudicate disagreements.
5. Freeze the dataset and record its SHA-256.
6. Retain difficult negatives: keyword-overlap false positives, semantically similar but ineligible roles, missing mandatory requirements, related-role matches, noisy/incomplete JDs and preference conflicts.
7. Record the ranking model/config version used for the baseline.

See `benchmark_status.json` for machine-readable lifecycle state.

## Regression gate

The repository contains `scripts/evaluate_ranking.py` for metrics and `scripts/ranking_regression_gate.py` for baseline comparison. `regression_policy.json` defines allowable degradation. `baseline.json` becomes authoritative once a human-verified benchmark is promoted.

CI is conditional on benchmark status being `validated`; until then it reports the benchmark as provisional rather than pretending synthetic scores are production evidence.

Required metrics: `precision_at_5`, `recall_at_5`, `ndcg_at_5`, and `mrr`.

CI also runs Python and frontend runtime dependency vulnerability audits.
