"""Per-flow evidence-stream score dumps (R3 Stage 0).

Every evaluated flow gets one row per (protocol, fold, seed, variant) with:
  * the raw evidence scores of every stream the model computed (``raw_sup``, ``raw_knn``, …);
  * each stream's benign surprisal under the *current* calibration state (``t_sup``, ``t_knn``, …);
  * every method's fused score and conformal p-value (``fused__<method>``, ``p__<method>``);
  * the classifier's Mondrian family p-value and predicted family index;
  * the flow's family, evaluation group (benign / known / unknown) and test-row position.

The dump is a passive observer: it reads the ``OSRScores`` already computed for evaluation and
re-applies the model's existing surprisal maps; it never changes model state, so records produced
with and without a dump are identical (checked by ``scripts/65_regression_gate.py``).

Files: ``<root>/<protocol>/<fold>__s<seed>__<variant>.parquet`` plus ``<root>/manifest.json``
(rows, columns and SHA-256 per file). The parquet files are large and git-ignored; the manifest
is small and can be committed.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd


def _safe(s: str) -> str:
    return re.sub(r"[^A-Za-z0-9._+-]+", "_", s)


class ScoreDump:
    def __init__(self, root: Path) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.manifest_path = self.root / "manifest.json"
        self.entries: dict[str, dict] = {}
        if self.manifest_path.exists():
            self.entries = json.loads(self.manifest_path.read_text(encoding="utf-8"))["files"]

    def __call__(self, key: dict, model, sc, fam: np.ndarray, groups: np.ndarray) -> None:
        n = len(fam)
        cols: dict[str, np.ndarray] = {
            "row": np.arange(n, dtype=np.int32),
            "family": np.asarray(fam).astype(str),
            "group": np.asarray(groups).astype(str),
        }
        for k, v in sc.raw.items():
            cols[f"raw_{k}"] = np.asarray(v, dtype=np.float64)
            if k in model.cdf_:
                cols[f"t_{k}"] = np.asarray(model.cdf_[k](v), dtype=np.float64)
        for m in sc.fused:
            cols[f"fused__{m}"] = np.asarray(sc.fused[m], dtype=np.float64)
            cols[f"p__{m}"] = np.asarray(sc.pvalue[m], dtype=np.float64)
        cols["p_family"] = np.asarray(sc.p_fam, dtype=np.float64)
        cols["pred_family_idx"] = np.asarray(sc.pred_family_idx, dtype=np.int16)
        df = pd.DataFrame(cols)
        for c in ("family", "group"):
            df[c] = df[c].astype("category")

        rel = Path(_safe(key["protocol"])) / f"{_safe(str(key['fold']))}__s{key['seed']}__{_safe(key['variant'])}.parquet"
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        df.to_parquet(path, compression="zstd", index=False)
        self.entries[rel.as_posix()] = {
            **{k: (str(v) if k == "fold" else v) for k, v in key.items()},
            "rows": int(n),
            "groups": {g: int((df["group"] == g).sum()) for g in ("benign", "known", "unknown")},
            "columns": list(df.columns),
            "streams": sorted(sc.raw),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        }
        self.manifest_path.write_text(json.dumps({"files": self.entries}, indent=1), encoding="utf-8")
