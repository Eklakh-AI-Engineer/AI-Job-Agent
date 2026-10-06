# Ranking Metrics

## Metrics implemented

| Metric | Definition | Use |
|---|---|---|
| Precision@K | Relevant results in top K / K | Top-of-list quality |
| Recall@K | Relevant results retrieved in top K / all relevant | Coverage |
| nDCG@K | Discounted gain normalized by ideal ranking | Ranking order quality |
| MRR | Reciprocal rank of first relevant result | First-good-result quality |
| Precision / Recall / F1 | Binary classification metrics | Eligibility/decision tasks |

All ranking metrics are computed per query and macro-averaged across query groups.

## Reproducible runner

`python scripts/evaluate_ranking.py` evaluates the current benchmark using its candidate order as the default baseline.

To evaluate a model/ranker, provide a JSON mapping of `query_id` to an ordered list of `job_id` values:

```json
{
  "Q-001": ["SYN-001", "SYN-003", "SYN-002", "SYN-004", "SYN-005"]
}
```

Then run:

```bash
python scripts/evaluate_ranking.py --predictions predictions.json
```

## Interpretation

Do not publish benchmark scores until the provisional synthetic cases are replaced or supplemented with human-verified labels from the actual job corpus.

Recommended v1 reporting:
- Precision@5
- Recall@5
- nDCG@5
- MRR
- hard-reject precision/recall
- skill extraction precision/recall/F1
- eligibility accuracy
- evidence correctness
- unsupported-claim rate