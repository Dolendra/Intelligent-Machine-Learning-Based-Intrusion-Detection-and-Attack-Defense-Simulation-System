"""Prepare CICIDS2017: load → clean → filter rare classes → split → save parquet."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ml.preprocessing.dataset import (
    clean_dataframe,
    filter_rare_labels,
    load_raw_csvs,
    save_processed,
    split_dataset,
    summarize_labels,
)
from ids_config import load_config


def main() -> None:
    cfg = load_config()
    print("Loading CICIDS2017 CSVs from", cfg["data"]["raw_dir"])
    print(f"sample_frac={cfg['data']['sample_frac']}")
    raw = load_raw_csvs()
    print(f"Raw rows: {len(raw):,}")
    cleaned = clean_dataframe(raw)
    print(f"Clean rows: {len(cleaned):,}")
    filtered = filter_rare_labels(cleaned)
    print(f"After rare-class filter: {len(filtered):,}")
    print("\nLabel distribution:")
    print(summarize_labels(filtered).to_string())
    splits = split_dataset(filtered)
    out = save_processed(splits)
    meta = {
        "n_train": len(splits["train"]),
        "n_val": len(splits["val"]),
        "n_test": len(splits["test"]),
        "labels": splits["train"]["Label"].value_counts().to_dict(),
        "n_features": len([c for c in splits["train"].columns if c not in ("Label", "is_attack")]),
        "sample_frac": cfg["data"]["sample_frac"],
        "min_class_count": cfg["data"].get("min_class_count", 50),
    }
    (out / "summary.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(f"\nSaved processed splits to {out}")
    print(json.dumps(meta, indent=2))


if __name__ == "__main__":
    main()
