"""Ranking and evaluation metrics for the candidate-job benchmark."""

from __future__ import annotations

import math
from typing import Iterable, Mapping, Sequence


def precision_at_k(relevances: Sequence[int], k: int) -> float:
    if k <= 0:
        raise ValueError("k must be positive")
    top = list(relevances[:k])
    return sum(r > 0 for r in top) / k


def recall_at_k(relevances: Sequence[int], k: int) -> float:
    if k <= 0:
        raise ValueError("k must be positive")
    total_relevant = sum(r > 0 for r in relevances)
    if total_relevant == 0:
        return 0.0
    return sum(r > 0 for r in relevances[:k]) / total_relevant


def reciprocal_rank(relevances: Sequence[int]) -> float:
    for rank, relevance in enumerate(relevances, start=1):
        if relevance > 0:
            return 1.0 / rank
    return 0.0


def ndcg_at_k(relevances: Sequence[int], k: int) -> float:
    if k <= 0:
        raise ValueError("k must be positive")

    def dcg(values: Sequence[int]) -> float:
        return sum(
            (2**relevance - 1) / math.log2(rank + 1)
            for rank, relevance in enumerate(values, start=1)
        )

    actual = dcg(list(relevances[:k]))
    ideal = dcg(sorted(relevances, reverse=True)[:k])
    return actual / ideal if ideal else 0.0


def binary_precision_recall_f1(
    predicted: Iterable[bool],
    actual: Iterable[bool],
) -> tuple[float, float, float]:
    predicted = list(predicted)
    actual = list(actual)
    if len(predicted) != len(actual):
        raise ValueError("predicted and actual must have equal length")

    tp = sum(p and a for p, a in zip(predicted, actual))
    fp = sum(p and not a for p, a in zip(predicted, actual))
    fn = sum(not p and a for p, a in zip(predicted, actual))

    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return precision, recall, f1


def evaluate_ranked_case(
    gold_relevance: Mapping[str, int],
    predicted_job_ids: Sequence[str],
    k: int = 5,
) -> dict[str, float]:
    """Score one query against a gold job-relevance mapping."""
    relevances = [gold_relevance.get(job_id, 0) for job_id in predicted_job_ids]
    return {
        f"precision@{k}": precision_at_k(relevances, k),
        f"recall@{k}": recall_at_k(relevances, k),
        f"ndcg@{k}": ndcg_at_k(relevances, k),
        "mrr": reciprocal_rank(relevances),
    }


def aggregate_metrics(cases: Sequence[Mapping[str, float]]) -> dict[str, float]:
    """Macro-average metrics across query groups."""
    if not cases:
        return {}
    keys = cases[0].keys()
    return {
        key: round(sum(float(case[key]) for case in cases) / len(cases), 4)
        for key in keys
    }
