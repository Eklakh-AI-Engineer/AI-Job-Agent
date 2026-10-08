#!/usr/bin/env python3
"""Fail CI when ranking metrics regress beyond the frozen policy."""
from __future__ import annotations
import argparse, json
from pathlib import Path

DEFAULT_POLICY = {"precision_at_5": 0.02, "recall_at_5": 0.02, "ndcg_at_5": 0.02, "mrr": 0.02}

def load(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    # Extract metrics from nested structure if present
    if isinstance(data, dict) and "metrics" in data:
        return data["metrics"]
    return data

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--latest", type=Path, required=True)
    parser.add_argument("--policy", type=Path)
    args = parser.parse_args()
    
    baseline = load(args.baseline)
    latest = load(args.latest)
    policy = load(args.policy) if args.policy else DEFAULT_POLICY
    
    regressions = []
    for metric, tolerance in policy.items():
        if metric not in baseline or metric not in latest:
            regressions.append(f"missing metric: {metric}")
            continue
        allowed = float(baseline[metric]) - float(tolerance)
        if float(latest[metric]) < allowed:
            regressions.append(f"{metric}: baseline={baseline[metric]:.6f}, latest={latest[metric]:.6f}, allowed_min={allowed:.6f}")
    
    if regressions:
        print("RANKING REGRESSION: FAILED")
        for item in regressions: 
            print(f"- {item}")
        return 1
    
    print("RANKING REGRESSION: PASSED")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
