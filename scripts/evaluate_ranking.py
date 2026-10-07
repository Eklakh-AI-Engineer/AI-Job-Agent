#!/usr/bin/env python3
"""Evaluate ranked job predictions against the frozen v1 benchmark.

Examples:
  python scripts/evaluate_ranking.py
  python scripts/evaluate_ranking.py --predictions docs/evaluation/predictions_benchmark_fixture_v1.json
  python scripts/evaluate_ranking.py --check-regression --output docs/evaluation/latest_regression.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "backend"))

from evaluation.hybrid_ranker import RANKING_VERSION
from backend.evaluation.metrics import aggregate_metrics, evaluate_ranked_case


DATASET = ROOT / "docs" / "evaluation" / "benchmark_job_ranking_v1.jsonl"
THRESHOLDS = ROOT / "docs" / "evaluation" / "ranking_regression_thresholds_v1.json"
DEFAULT_PREDICTIONS = ROOT / "docs" / "evaluation" / "predictions_benchmark_fixture_v1.json"


def load_cases() -> list[dict]:
    return [
        json.loads(line)
        for line in DATASET.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def dataset_sha256() -> str:
    return hashlib.sha256(DATASET.read_bytes()).hexdigest()


def load_predictions(path: Path) -> dict[str, list[str]]:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def evaluate(predictions: dict[str, list[str]], k: int) -> dict[str, float]:
    case_metrics = []
    for case in load_cases():
        gold = {item["job_id"]: item["relevance"] for item in case["candidates"]}
        ranked = predictions.get(
            case["query_id"],
            [item["job_id"] for item in case["candidates"]],
        )
        case_metrics.append(evaluate_ranked_case(gold, ranked, k))
    return aggregate_metrics(case_metrics)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--predictions", type=Path, default=DEFAULT_PREDICTIONS)
    parser.add_argument("--k", type=int, default=5)
    parser.add_argument("--check-regression", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    metrics = evaluate(load_predictions(args.predictions), args.k)
    report = {
        "benchmark_version": "50-query-v1",
        "dataset_sha256": dataset_sha256(),
        "ranking_version": RANKING_VERSION,
        "prediction_source": str(args.predictions.relative_to(ROOT)) if args.predictions.exists() else "benchmark_default_order",
        "metrics": metrics,
    }

    if args.check_regression:
        thresholds = json.loads(THRESHOLDS.read_text(encoding="utf-8"))
        failures = {
            name: {"actual": metrics.get(name, 0.0), "minimum": minimum}
            for name, minimum in thresholds["minimums"].items()
            if metrics.get(name, 0.0) < minimum
        }
        report["thresholds"] = thresholds
        report["passed"] = not failures
        report["failures"] = failures
        if failures:
            print(json.dumps(report, indent=2, sort_keys=True))
            if args.output:
                args.output.parent.mkdir(parents=True, exist_ok=True)
                args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            return 1

    print(json.dumps(report, indent=2, sort_keys=True))
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
