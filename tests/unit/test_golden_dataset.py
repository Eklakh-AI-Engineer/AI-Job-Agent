"""Validate the frozen 50-query ranking benchmark structure."""

import json
from pathlib import Path


DATASET = Path(__file__).parents[2] / "docs" / "evaluation" / "benchmark_job_ranking_v1.jsonl"


def test_benchmark_has_50_queries_and_250_candidates():
    rows = [json.loads(line) for line in DATASET.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(rows) == 50
    assert len({row["query_id"] for row in rows}) == 50
    assert all(row["benchmark_version"] == "50-query-v1" for row in rows)
    assert all(row["status"] == "benchmark-fixture" for row in rows)
    assert all(row["human_verified"] is False for row in rows)
    assert all(row["review_state"] == "machine_generated_fixture" for row in rows)
    assert all(len(row["candidates"]) == 5 for row in rows)
    assert all(
        all(0 <= candidate["relevance"] <= 3 for candidate in row["candidates"])
        for row in rows
    )
    assert sum(len(row["candidates"]) for row in rows) == 250


def test_benchmark_contains_difficult_negative_metadata():
    rows = [json.loads(line) for line in DATASET.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert all("gold_relevant_job_ids" in row for row in rows)
    assert all("difficult_negative_job_ids" in row for row in rows)
    assert all("reviewer_rationale" in row for row in rows)
