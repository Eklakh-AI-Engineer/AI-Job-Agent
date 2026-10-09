#!/usr/bin/env python3
"""Fail closed unless the ranking baseline and latest result are authoritative.

The synthetic benchmark comparison is available only through the explicit
--allow-non-production-baseline flag. That mode checks plumbing, not product
ranking quality and must never be used as a release gate.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

DEFAULT_POLICY = {
    "precision_at_5": 0.02,
    "recall_at_5": 0.02,
    "ndcg_at_5": 0.02,
    "mrr": 0.02,
}


def load_document(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path}: expected a JSON object")
    return data


def metrics_from(document: dict[str, Any]) -> dict[str, Any]:
    metrics = document.get("metrics", document)
    if not isinstance(metrics, dict):
        raise ValueError("metrics must be a JSON object")
    return metrics


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--latest", type=Path, required=True)
    parser.add_argument("--policy", type=Path)
    parser.add_argument(
        "--allow-non-production-baseline",
        action="store_true",
        help="Explicitly allow a synthetic/reference comparison for CI plumbing only.",
    )
    args = parser.parse_args()

    try:
        baseline_doc = load_document(args.baseline)
        latest_doc = load_document(args.latest)
        policy_doc = load_document(args.policy) if args.policy else DEFAULT_POLICY
        baseline = metrics_from(baseline_doc)
        latest = metrics_from(latest_doc)
        policy = metrics_from(policy_doc)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"RANKING REGRESSION: BLOCKED — invalid input: {exc}")
        return 2

    baseline_authoritative = baseline_doc.get("production_authoritative") is True
    latest_authoritative = latest_doc.get("production_authoritative") is True

    if baseline_authoritative != latest_authoritative:
        print("RANKING REGRESSION: BLOCKED — baseline/latest authority status differs")
        return 2

    if not baseline_authoritative:
        if not args.allow_non_production_baseline:
            print(
                "RANKING REGRESSION: BLOCKED — baseline/latest are not marked "
                "production_authoritative=true. Map adjudicated labels to real "
                "persisted jobs and generate fresh runtime-ranker metrics first."
            )
            return 2
        if (
            baseline_doc.get("production_authoritative") is not False
            or latest_doc.get("production_authoritative") is not False
        ):
            print(
                "RANKING REGRESSION: BLOCKED — non-production mode requires "
                "explicit production_authoritative=false in both files"
            )
            return 2
        print(
            "MODE: synthetic/reference comparison only; this is not a production "
            "ranking-quality gate."
        )
    else:
        baseline_version = baseline_doc.get("ranking_version")
        latest_version = latest_doc.get("ranking_version")
        if not baseline_version or baseline_version != latest_version:
            print(
                "RANKING REGRESSION: BLOCKED — ranking_version is missing or "
                "differs between baseline and latest"
            )
            return 2

    benchmark_id = baseline_doc.get("benchmark")
    if not benchmark_id or benchmark_id != latest_doc.get("benchmark"):
        print("RANKING REGRESSION: BLOCKED — benchmark identifiers differ or are missing")
        return 2

    baseline_hash = (
        baseline_doc.get("dataset_sha256")
        or baseline_doc.get("final_workbook_sha256")
        or baseline_doc.get("benchmark_sha256")
    )
    latest_hash = (
        latest_doc.get("dataset_sha256")
        or latest_doc.get("final_workbook_sha256")
        or latest_doc.get("benchmark_sha256")
    )
    if not baseline_hash or baseline_hash != latest_hash:
        print("RANKING REGRESSION: BLOCKED — dataset fingerprints differ or are missing")
        return 2

    regressions: list[str] = []
    for metric, tolerance_value in policy.items():
        if metric not in baseline or metric not in latest:
            regressions.append(f"missing metric: {metric}")
            continue
        try:
            baseline_value = float(baseline[metric])
            latest_value = float(latest[metric])
            tolerance = float(tolerance_value)
        except (TypeError, ValueError):
            regressions.append(f"non-numeric metric or tolerance: {metric}")
            continue
        if not 0 <= tolerance <= 1:
            regressions.append(f"invalid tolerance for {metric}: {tolerance}")
            continue
        allowed = baseline_value - tolerance
        if latest_value < allowed:
            regressions.append(
                f"{metric}: baseline={baseline_value:.6f}, latest={latest_value:.6f}, "
                f"allowed_min={allowed:.6f}"
            )

    if regressions:
        print("RANKING REGRESSION: FAILED")
        for item in regressions:
            print(f"- {item}")
        return 1

    print("RANKING REGRESSION: PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
