"""Validate the provisional golden ranking benchmark structure."""

import json
from pathlib import Path


DATASET = Path(__file__).parents[2] / "docs" / "evaluation" / "golden_job_ranking_v1.jsonl"


def test_golden_dataset_has_50_provisional_queries():
    rows = [json.loads(line) for line in DATASET.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(rows) == 50
    assert len({row["query_id"] for row in rows}) == 50
    assert all(row["status"] == "provisional" for row in rows)
    assert all(row["human_verified"] is False for row in rows)
    assert all(len(row["candidates"]) == 5 for row in rows)
    assert all(
        all(0 <= candidate["relevance"] <= 3 for candidate in row["candidates"])
        for row in rows
    )
