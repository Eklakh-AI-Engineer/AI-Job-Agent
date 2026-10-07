# Ranking baseline v1

The regression infrastructure now has a committed baseline and latest reference.

| Metric | Baseline | Latest |
|---|---:|---:|
| Precision@5 | 1.0000 | 1.0000 |
| Recall@5 | 1.0000 | 1.0000 |
| nDCG@5 | 1.0000 | 1.0000 |
| MRR | 1.0000 | 1.0000 |

**Important:** these values come from the benchmark fixture's default candidate order, which is already ordered by its provisional relevance labels. They prove that the regression-gate plumbing works; they are **not** evidence that the production ranker achieves perfect ranking quality.

The baseline must be replaced after benchmark promotion using real persisted jobs, independent human labels, adjudication, and a frozen SHA-256 dataset.

The CI regression gate is enforceable whenever the committed baseline/latest artifacts exist. Benchmark promotion remains a separate release gate.
