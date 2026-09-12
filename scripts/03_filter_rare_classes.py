"""Drop ultra-rare classes that break stratified splits / macro metrics."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ml.preprocessing.dataset import load_processed, save_processed, split_dataset, clean_dataframe, load_raw_csvs


MIN_COUNT = 50


def main() -> None:
    # Re-clean from raw with current config, then drop rare labels
    raw = load_raw_csvs()
    df = clean_dataframe(raw)
    counts = df["Label"].value_counts()
    keep = counts[counts >= MIN_COUNT].index
    filtered = df[df["Label"].isin(keep)].reset_index(drop=True)
    print("Kept labels:", filtered["Label"].value_counts().to_dict())
    splits = split_dataset(filtered)
    out = save_processed(splits)
    print("Saved to", out)


if __name__ == "__main__":
    main()
