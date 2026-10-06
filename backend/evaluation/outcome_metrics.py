"""Offline application-outcome analytics.

Pure functions over exported application/event rows. No mutation or automatic
ranking retraining.
"""
from __future__ import annotations
from collections import Counter, defaultdict
from statistics import mean
from typing import Iterable, Mapping, Sequence

def application_funnel(statuses: Iterable[str]) -> dict[str, int]:
    counts = Counter(statuses)
    return {status: counts.get(status, 0) for status in ("Discovered", "Matched", "Approved", "Applied", "Rejected")}

def transition_rate(from_status: str, to_status: str, events: Sequence[Mapping[str, object]]) -> float:
    starts = sum(event.get("from_status") == from_status for event in events)
    successes = sum(event.get("from_status") == from_status and event.get("to_status") == to_status for event in events)
    return successes / starts if starts else 0.0

def apply_rate_by_score_bucket(rows: Iterable[Mapping[str, object]]) -> dict[str, float]:
    buckets: dict[str, list[bool]] = defaultdict(list)
    for row in rows:
        score = row.get("match_score")
        if not isinstance(score, (int, float)):
            continue
        bucket = "0-39" if score < 40 else "40-59" if score < 60 else "60-79" if score < 80 else "80-100"
        buckets[bucket].append(row.get("status") == "Applied")
    return {bucket: mean(values) for bucket, values in sorted(buckets.items())}

def source_apply_rate(rows: Iterable[Mapping[str, object]]) -> dict[str, float]:
    groups: dict[str, list[bool]] = defaultdict(list)
    for row in rows:
        groups[str(row.get("source") or "unknown")].append(row.get("status") == "Applied")
    return {source: mean(values) for source, values in sorted(groups.items())}

def outcome_report(rows: Iterable[Mapping[str, object]]) -> dict[str, object]:
    materialized = list(rows)
    return {"row_count": len(materialized), "funnel": application_funnel(row["status"] for row in materialized), "apply_rate_by_score_bucket": apply_rate_by_score_bucket(materialized), "source_apply_rate": source_apply_rate(materialized)}
