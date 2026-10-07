#!/usr/bin/env python3
"""Evaluate ranked job predictions against the v1 benchmark.

Usage:
  python scripts/evaluate_ranking.py
  python scripts/evaluate_ranking.py --predictions predictions.json
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from backend.evaluation.metrics import aggregate_metrics, evaluate_ranked_case


ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "docs" / "evaluation" / "golden_job_ranking_v1.jsonl"


def load_cases() -> list[dict]:
    return [
        json.loads(line)
        for line in DATASET.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--predictions", type=Path)
    parser.add_argument("--k", type=int, default=5)
    args = parser.parse_args()

    predictions = {}
    if args.predictions:
        predictions = json.loads(args.predictions.read_text(encoding="utf-8"))

    case_metrics = []
    for case in load_cases():
        gold = {item["job_id"]: item["relevance"] for item in case["candidates"]}
        ranked = predictions.get(
            case["query_id"],
            [item["job_id"] for item in case["candidates"]],
        )
        case_metrics.append(evaluate_ranked_case(gold, ranked, args.k))

    metrics = aggregate_metrics(case_metrics)
    print(json.dumps(metrics, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
