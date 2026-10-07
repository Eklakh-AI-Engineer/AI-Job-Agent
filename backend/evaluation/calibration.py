"""Deterministic post-hoc calibration for ranking scores.

This module deliberately does not change ordering: it maps the existing 0-100
score to an estimated probability of relevance using a fitted sigmoid. The
calibrator must be fitted on labels independent of the benchmark used for
release reporting.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Sequence


CALIBRATION_VERSION = "sigmoid-v1"


@dataclass(frozen=True)
class SigmoidCalibrator:
    intercept: float
    slope: float
    version: str = CALIBRATION_VERSION

    def probability(self, raw_score: float) -> float:
        z = max(-60.0, min(60.0, self.intercept + self.slope * float(raw_score)))
        return round(1.0 / (1.0 + math.exp(-z)), 6)

    def score(self, raw_score: float) -> float:
        return round(self.probability(raw_score) * 100.0, 2)


def fit_sigmoid(
    raw_scores: Sequence[float],
    labels: Sequence[int],
    *,
    iterations: int = 100,
    l2: float = 1e-3,
) -> SigmoidCalibrator:
    """Fit P(relevant | raw_score) with Newton updates.

    Labels may be 0/1 or graded relevance; graded labels are treated as
    relevant when >0. A minimum of two distinct scores and both classes are
    required so the fit cannot silently collapse.
    """
    if len(raw_scores) != len(labels) or len(raw_scores) < 8:
        raise ValueError("Need at least 8 score/label pairs of equal length")
    y = [1.0 if int(label) > 0 else 0.0 for label in labels]
    if len(set(y)) < 2 or len(set(float(x) for x in raw_scores)) < 2:
        raise ValueError("Calibration data must contain both classes and varied scores")

    mean = sum(float(x) for x in raw_scores) / len(raw_scores)
    scale = max(1.0, max(abs(float(x) - mean) for x in raw_scores))
    xs = [(float(x) - mean) / scale for x in raw_scores]
    intercept = 0.0
    slope = 0.0

    for _ in range(iterations):
        g0 = g1 = h00 = h01 = h11 = 0.0
        for x, target in zip(xs, y):
            z = max(-30.0, min(30.0, intercept + slope * x))
            p = 1.0 / (1.0 + math.exp(-z))
            error = p - target
            weight = p * (1.0 - p)
            g0 += error
            g1 += error * x
            h00 += weight
            h01 += weight * x
            h11 += weight * x * x
        h00 += l2
        h11 += l2
        determinant = h00 * h11 - h01 * h01
        if abs(determinant) < 1e-12:
            break
        delta0 = (h11 * g0 - h01 * g1) / determinant
        delta1 = (-h01 * g0 + h00 * g1) / determinant
        intercept -= delta0
        slope -= delta1
        if abs(delta0) + abs(delta1) < 1e-7:
            break

    # Convert back to the original 0-100 score scale.
    original_slope = slope / scale
    original_intercept = intercept - original_slope * mean
    return SigmoidCalibrator(original_intercept, original_slope)
