"""Audit label normalization and rare-class filtering for the report."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pandas as pd

from ids_config import load_config, resolve_path
from ml.preprocessing.dataset import LABEL_MAP, list_csv_files, normalize_labels


def main() -> None:
    cfg = load_config()
    out_dir = resolve_path(cfg["models"]["output_dir"])
    out_dir.mkdir(parents=True, exist_ok=True)
    min_count = int(cfg["data"].get("min_class_count", 50))

    report: dict = {
        "experiment": "label_and_rare_class_audit",
        "min_class_count": min_count,
        "label_map_entries": len(LABEL_MAP),
        "mapping_table": [{"original": k, "normalized": v} for k, v in sorted(LABEL_MAP.items())],
        "status": "ok",
    }

    try:
        frames = []
        for path in list_csv_files()[:4]:
            df = pd.read_csv(path, low_memory=False, nrows=25000)
            df.columns = [c.strip() for c in df.columns]
            if "Label" in df.columns:
                frames.append(df[["Label"]])
        if not frames:
            raise FileNotFoundError("No Label columns found in raw CSVs")
        sample = pd.concat(frames, ignore_index=True)
        raw_labels = sample["Label"].astype(str).str.strip()
        mapped = normalize_labels(raw_labels)
        pairs = (
            pd.DataFrame({"original": raw_labels, "normalized": mapped})
            .drop_duplicates()
            .sort_values(["normalized", "original"])
        )
        other = pairs[pairs["normalized"] == "Other"]
        report["sample_rows"] = int(len(sample))
        report["unique_original_labels"] = int(raw_labels.nunique())
        report["unique_normalized_labels"] = int(mapped.nunique())
        report["mapping_examples"] = pairs.head(50).to_dict(orient="records")
        report["unknown_or_other"] = {
            "count_unique": int(other["original"].nunique()),
            "examples": other["original"].head(20).tolist(),
        }
    except Exception as exc:  # noqa: BLE001
        report["status"] = "partial"
        report["reason"] = f"CSV sample audit skipped: {exc}"

    processed = resolve_path(cfg["data"]["processed_dir"]) / "train.parquet"
    if processed.exists():
        train = pd.read_parquet(processed)
        counts = train["Label"].value_counts()
        report["processed_train"] = {
            "n_rows": int(len(train)),
            "n_classes": int(counts.shape[0]),
            "counts": counts.to_dict(),
            "classes_below_min_count": {k: int(v) for k, v in counts.items() if int(v) < min_count},
        }
    else:
        report["processed_train"] = None
        report["note"] = "Run scripts/01_prepare_data.py to include processed train class counts."

    path = out_dir / "label_audit_report.json"
    path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Wrote {path} status={report['status']}")


if __name__ == "__main__":
    main()
