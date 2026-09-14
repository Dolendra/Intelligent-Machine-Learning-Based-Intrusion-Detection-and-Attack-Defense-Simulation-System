"""Aggregate trial metrics for empirical mitigation experiments."""
from __future__ import annotations

import math
import statistics
from typing import Any


def _percentile(samples: list[float], p: float) -> float | None:
    if not samples:
        return None
    ordered = sorted(samples)
    if len(ordered) == 1:
        return round(ordered[0], 6)
    rank = (len(ordered) - 1) * p
    lo = math.floor(rank)
    hi = math.ceil(rank)
    if lo == hi:
        return round(ordered[lo], 6)
    w = rank - lo
    return round(ordered[lo] * (1 - w) + ordered[hi] * w, 6)


def summarize(values: list[float | int | None]) -> dict[str, Any]:
    nums = [float(v) for v in values if v is not None]
    if not nums:
        return {
            "n": 0,
            "mean": None,
            "median": None,
            "stdev": None,
            "min": None,
            "max": None,
            "p95": None,
        }
    return {
        "n": len(nums),
        "mean": round(statistics.fmean(nums), 6),
        "median": round(statistics.median(nums), 6),
        "stdev": round(statistics.stdev(nums), 6) if len(nums) > 1 else 0.0,
        "min": round(min(nums), 6),
        "max": round(max(nums), 6),
        "p95": _percentile(nums, 0.95),
    }


def mitigation_effectiveness(
    *,
    baseline_attack_accepted_rate: float,
    defended_attack_accepted_rate: float,
) -> float:
    """Fraction of baseline accepted-attack rate removed by defense.

    1.0 = all previously accepted attack traffic blocked; 0.0 = no change.
    Can be negative if defended window somehow accepted more (should not happen).
    """
    if baseline_attack_accepted_rate <= 0:
        return 0.0
    return round(
        (baseline_attack_accepted_rate - defended_attack_accepted_rate) / baseline_attack_accepted_rate,
        6,
    )
