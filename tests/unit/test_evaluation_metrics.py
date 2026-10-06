"""Tests for ranking and binary evaluation metrics."""

from backend.evaluation.metrics import (
    aggregate_metrics,
    binary_precision_recall_f1,
    ndcg_at_k,
    precision_at_k,
    recall_at_k,
    reciprocal_rank,
)


def test_precision_recall_mrr():
    relevances = [3, 0, 2, 0, 0]
    assert precision_at_k(relevances, 3) == 2 / 3
    assert recall_at_k(relevances, 3) == 1.0
    assert reciprocal_rank(relevances) == 1.0


def test_ndcg_is_perfect_for_ideal_order():
    assert ndcg_at_k([3, 2, 1, 0], 4) == 1.0


def test_binary_precision_recall_f1():
    precision, recall, f1 = binary_precision_recall_f1(
        [True, True, False, False],
        [True, False, True, False],
    )
    assert round(precision, 4) == 0.5
    assert round(recall, 4) == 0.5
    assert round(f1, 4) == 0.5


def test_aggregate_metrics():
    result = aggregate_metrics(
        [{"mrr": 1.0, "ndcg@5": 0.8}, {"mrr": 0.5, "ndcg@5": 0.6}]
    )
    assert result == {"mrr": 0.75, "ndcg@5": 0.7}
