# Human Benchmark v1 -> Master Scoreboard

The canonical workflow is:

1. Start from Human_Benchmark_Labeled_v1.xlsx.
2. Run scripts/evaluate_human_benchmark.py.
3. Review AI_Predictions_v1.jsonl and Evaluation_Results_v1.json.
4. Review MASTER_SCOREBOARD.md.
5. Only use --promote --real-persisted-jobs when the workbook is independently human-labeled, frozen, and its rows map to real persisted/discovered jobs.
6. Never edit AI or human labels during metric calculation.

Example:

    python scripts/evaluate_human_benchmark.py docs/evaluation/Human_Benchmark_Labeled_v1.xlsx --output-dir docs/evaluation/results_v1

The default result is human_labeled_pending_promotion, which keeps the regression gate from treating an unverified dataset as production evidence.

## Required scoreboard

- Classification: accuracy, macro precision/recall/F1, binary confusion matrix
- Agreement: exact, ±1, Cohen's kappa, quadratic weighted kappa
- Ranking: Precision@5, Recall@5, nDCG@5, MRR when query groups contain multiple candidates
- Dataset: row count, query count, workbook SHA-256
- Promotion state: human verified, frozen, real persisted jobs, validated

The evaluator is intentionally conservative: it fails on missing required columns or malformed labels rather than silently guessing.
