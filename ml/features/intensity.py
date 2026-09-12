"""Traffic intensity from flow features using training-reference percentiles."""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from ids_config import load_config, resolve_path

REF_KEYS = ("Flow Packets/s", "Flow Bytes/s")


def build_intensity_reference(train_df: pd.DataFrame) -> dict[str, Any]:
    """Fit percentile reference on training flows (no leakage from val/test)."""
    ref: dict[str, Any] = {"features": {}, "method": "max_of_feature_percentile_ranks"}
    for col in REF_KEYS:
        if col not in train_df.columns:
            continue
        vals = pd.to_numeric(train_df[col], errors="coerce").replace([np.inf, -np.inf], np.nan).dropna().abs()
        if vals.empty:
            continue
        qs = [50, 75, 90, 95, 99]
        ref["features"][col] = {
            "percentiles": {str(q): float(np.percentile(vals, q)) for q in qs},
            "p99": float(np.percentile(vals, 99)),
            "max": float(vals.max()),
        }
    return ref


def save_intensity_reference(ref: dict[str, Any], path: Path | str | None = None) -> Path:
    cfg = load_config()
    out = Path(path) if path else resolve_path(cfg["models"]["output_dir"]) / "intensity_reference.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(ref, indent=2), encoding="utf-8")
    return out


@lru_cache(maxsize=1)
def load_intensity_reference() -> dict[str, Any] | None:
    cfg = load_config()
    path = resolve_path(cfg["models"]["output_dir"]) / "intensity_reference.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def clear_intensity_cache() -> None:
    load_intensity_reference.cache_clear()


def _rank_vs_percentiles(value: float, percentiles: dict[str, float]) -> float:
    """Map absolute value to ~0–1 using training percentile anchors."""
    v = abs(float(value))
    ordered = sorted((int(k), float(p)) for k, p in percentiles.items())
    if not ordered:
        return min(1.0, v / 1e5)
    if v <= ordered[0][1]:
        return ordered[0][0] / 100.0 * (v / ordered[0][1] if ordered[0][1] else 0.0)
    for (q0, p0), (q1, p1) in zip(ordered, ordered[1:]):
        if v <= p1:
            if p1 == p0:
                return q1 / 100.0
            t = (v - p0) / (p1 - p0)
            return (q0 + t * (q1 - q0)) / 100.0
    # Above p99 → approach 1.0
    p99 = ordered[-1][1]
    if p99 <= 0:
        return 1.0
    return min(1.0, 0.99 + 0.01 * min(1.0, (v - p99) / max(p99, 1.0)))


def intensity_from_features(features: dict[str, float]) -> float | None:
    """Return 0–1 intensity; prefer percentile reference, else legacy fallback."""
    ref = load_intensity_reference()
    scores: list[float] = []
    if ref and ref.get("features"):
        for col, stats in ref["features"].items():
            if col in features:
                scores.append(_rank_vs_percentiles(float(features[col]), stats["percentiles"]))
        if scores:
            return float(min(1.0, max(scores)))
    # Legacy fallback
    for key in REF_KEYS:
        if key in features:
            return float(min(1.0, abs(float(features[key])) / 1e5))
    return None
