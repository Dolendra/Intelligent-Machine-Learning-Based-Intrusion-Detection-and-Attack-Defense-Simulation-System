"""Validate flow feature frames against the frozen CICIDS2017 schema."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd

from ingestion.schema_info import expected_feature_names


@dataclass
class SchemaValidationResult:
    ok: bool
    feature_count: int
    missing: list[str] = field(default_factory=list)
    extra: list[str] = field(default_factory=list)
    non_numeric: list[str] = field(default_factory=list)
    message: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "feature_count": self.feature_count,
            "missing": self.missing,
            "extra": self.extra,
            "non_numeric": self.non_numeric,
            "message": self.message,
        }


METADATA_COLS = {"Label", "is_attack", "Flow ID", "Timestamp", "Source IP", "Destination IP", "Source Port"}


def align_dataframe(df: pd.DataFrame, *, fill_missing: bool = False) -> tuple[pd.DataFrame, SchemaValidationResult]:
    """Drop metadata, validate/align to expected feature order."""
    expected = expected_feature_names()
    work = df.drop(columns=[c for c in df.columns if c in METADATA_COLS], errors="ignore").copy()
    missing = [c for c in expected if c not in work.columns]
    extra = [c for c in work.columns if c not in expected]
    if missing and not fill_missing:
        result = SchemaValidationResult(
            ok=False,
            feature_count=len(expected),
            missing=missing,
            extra=extra,
            message=f"Missing {len(missing)} required feature columns",
        )
        return work, result
    if fill_missing:
        for col in missing:
            work[col] = 0.0
    aligned = work.reindex(columns=expected)
    non_numeric: list[str] = []
    for col in expected:
        if not pd.api.types.is_numeric_dtype(aligned[col]):
            coerced = pd.to_numeric(aligned[col], errors="coerce")
            if coerced.isna().any() and aligned[col].astype(str).str.len().gt(0).any():
                non_numeric.append(col)
            aligned[col] = coerced
        else:
            aligned[col] = pd.to_numeric(aligned[col], errors="coerce")

    arr = aligned.to_numpy(dtype=float, copy=True)
    if not np.isfinite(arr).all():
        if not fill_missing:
            result = SchemaValidationResult(
                ok=False,
                feature_count=len(expected),
                missing=[],
                extra=extra,
                non_numeric=non_numeric,
                message="NaN/Inf present after numeric coercion",
            )
            return aligned, result
        arr = np.nan_to_num(arr, nan=0.0, posinf=0.0, neginf=0.0)
        aligned = pd.DataFrame(arr, columns=expected)

    ok = len(non_numeric) == 0 and (not missing or fill_missing)
    result = SchemaValidationResult(
        ok=ok,
        feature_count=len(expected),
        missing=[] if fill_missing else missing,
        extra=extra,
        non_numeric=non_numeric,
        message="ok" if ok else "validation issues",
    )
    return aligned, result


def rows_as_feature_dicts(df: pd.DataFrame) -> list[dict[str, float]]:
    expected = expected_feature_names()
    out: list[dict[str, float]] = []
    for _, row in df.iterrows():
        out.append({c: float(row[c]) for c in expected})
    return out
