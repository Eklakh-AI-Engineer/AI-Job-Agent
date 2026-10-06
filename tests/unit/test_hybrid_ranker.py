"""Regression coverage for candidate-job hybrid ranking primitives."""

from backend.evaluation.hybrid_ranker import (
    RANKING_VERSION,
    RANKING_WEIGHTS,
    cosine_similarity,
    semantic_score,
)


def test_ranking_weights_sum_to_one():
    assert RANKING_VERSION == "hybrid-v1"
    assert sum(RANKING_WEIGHTS.values()) == 1.0


def test_cosine_similarity_and_semantic_score():
    assert cosine_similarity([1.0, 0.0], [1.0, 0.0]) == 1.0
    assert cosine_similarity([1.0, 0.0], [0.0, 1.0]) == 0.0
    assert semantic_score(1.0) == 100.0
    assert semantic_score(0.0) == 50.0


def test_semantic_score_is_bounded():
    assert semantic_score(-1.0) == 0.0
    assert semantic_score(1.0) == 100.0
