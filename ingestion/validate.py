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
    rows_in: int = 0
    rows_valid: int = 0
    rejected_rows: list[dict[str, Any]] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "feature_count": self.feature_count,
            "missing": self.missing,
            "extra": self.extra,
            "non_numeric": self.non_numeric,
            "message": self.message,
            "rows_in": self.rows_in,
            "rows_valid": self.rows_valid,
            "rejected_rows": self.rejected_rows,
        }


MAX_REJECTED_REPORTED = 50


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
    rows_in = len(aligned)
    rejected: list[dict[str, Any]] = []
    finite = np.isfinite(arr)
    if not finite.all():
        if fill_missing:
            # Explicit CLI opt-in only (ingestion --fill-missing): zero-fill, reported below.
            arr = np.nan_to_num(arr, nan=0.0, posinf=0.0, neginf=0.0)
            aligned = pd.DataFrame(arr, columns=expected, index=aligned.index)
        else:
            # R-11 (ML-8): per-row policy, consistent with training (which dropped non-finite
            # rows). A row with NaN / Inf / non-numeric values is rejected with its CSV line
            # number; the remaining rows are still scored. Previously one bad cell (e.g.
            # CICFlowMeter's "Infinity" for zero-duration flows) rejected the whole file.
            bad = ~finite.all(axis=1)
            for pos in np.flatnonzero(bad)[:MAX_REJECTED_REPORTED]:
                cols = [expected[j] for j in np.flatnonzero(~finite[pos])]
                rejected.append({"row": int(pos) + 2, "reason": "non-finite or non-numeric value",
                                 "columns": cols[:8]})
            aligned = aligned.loc[~bad].reset_index(drop=True)
    rows_valid = len(aligned)
    n_rejected = rows_in - rows_valid

    ok = rows_valid > 0 and (not missing or fill_missing)
    if ok:
        message = "ok" if n_rejected == 0 else f"ok; {n_rejected} row(s) rejected (non-finite or non-numeric)"
    elif rows_in and rows_valid == 0:
        message = "no valid rows: every row has NaN/Inf or non-numeric values"
    else:
        message = "validation issues"
    result = SchemaValidationResult(
        ok=ok,
        feature_count=len(expected),
        missing=[] if fill_missing else missing,
        extra=extra,
        non_numeric=non_numeric,
        message=message,
        rows_in=rows_in,
        rows_valid=rows_valid,
        rejected_rows=rejected,
    )
    return aligned, result


def rows_as_feature_dicts(df: pd.DataFrame) -> list[dict[str, float]]:
    expected = expected_feature_names()
    out: list[dict[str, float]] = []
    for _, row in df.iterrows():
        out.append({c: float(row[c]) for c in expected})
    return out
