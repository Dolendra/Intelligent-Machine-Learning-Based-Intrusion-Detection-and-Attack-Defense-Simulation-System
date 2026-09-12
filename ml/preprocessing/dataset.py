"""Dataset loading, cleaning, and splitting for CICIDS2017."""
from __future__ import annotations

from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

from ids_config import load_config, resolve_path

# Normalize noisy CICIDS2017 label strings into stable families
LABEL_MAP = {
    "BENIGN": "BENIGN",
    "DoS Hulk": "DoS",
    "DoS GoldenEye": "DoS",
    "DoS slowloris": "DoS",
    "DoS Slowhttptest": "DoS",
    "DDoS": "DDoS",
    "PortScan": "PortScan",
    "FTP-Patator": "BruteForce",
    "SSH-Patator": "BruteForce",
    "Web Attack – Brute Force": "WebAttack",
    "Web Attack – XSS": "WebAttack",
    "Web Attack – Sql Injection": "WebAttack",
    "Web Attack ? Brute Force": "WebAttack",
    "Web Attack ? XSS": "WebAttack",
    "Web Attack ? Sql Injection": "WebAttack",
    "Bot": "Bot",
    "Infiltration": "Infiltration",
    "Heartbleed": "Heartbleed",
}


def _strip_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [c.strip() for c in df.columns]
    return df


def list_csv_files(raw_dir: Path | None = None) -> list[Path]:
    cfg = load_config()
    directory = raw_dir or resolve_path(cfg["data"]["raw_dir"])
    files = sorted(directory.glob("*.csv"))
    if not files:
        raise FileNotFoundError(f"No CSV files found in {directory}")
    return files


def load_raw_csvs(
    files: Iterable[Path] | None = None,
    sample_frac: float | None = None,
    random_state: int | None = None,
    nrows: int | None = None,
) -> pd.DataFrame:
    """Load and concatenate CICIDS2017 MachineLearningCVE CSVs."""
    cfg = load_config()
    sample_frac = cfg["data"]["sample_frac"] if sample_frac is None else sample_frac
    random_state = cfg["data"]["random_state"] if random_state is None else random_state
    paths = list(files) if files is not None else list_csv_files()

    frames: list[pd.DataFrame] = []
    for path in paths:
        df = pd.read_csv(path, low_memory=False, nrows=nrows)
        df = _strip_columns(df)
        df["__source_file"] = path.name
        if sample_frac < 1.0:
            df = df.sample(frac=sample_frac, random_state=random_state)
        frames.append(df)

    combined = pd.concat(frames, ignore_index=True)
    return combined


def normalize_labels(series: pd.Series) -> pd.Series:
    cleaned = series.astype(str).str.strip()
    # Fix common encoding artifacts for web-attack labels
    cleaned = cleaned.str.replace("\u2013", "-", regex=False)
    cleaned = cleaned.str.replace("–", "-", regex=False)

    def map_one(label: str) -> str:
        if label in LABEL_MAP:
            return LABEL_MAP[label]
        # Fuzzy web-attack variants
        low = label.lower()
        if "web attack" in low:
            return "WebAttack"
        if label.startswith("DoS"):
            return "DoS"
        return LABEL_MAP.get(label, "Other")

    return cleaned.map(map_one)


def clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Remove duplicates, NaN/Inf, drop leakage columns, normalize labels."""
    cfg = load_config()
    df = _strip_columns(df)

    drop_cols = [c for c in cfg["data"].get("drop_columns", []) if c in df.columns]
    if "__source_file" in df.columns:
        drop_cols = list(set(drop_cols) | {"__source_file"})
    df = df.drop(columns=drop_cols, errors="ignore")

    if "Label" not in df.columns:
        raise ValueError("Expected a 'Label' column in the dataset")

    df["Label"] = normalize_labels(df["Label"])
    df["is_attack"] = (df["Label"] != "BENIGN").astype(int)

    # Numeric coercion for feature columns
    feature_cols = [c for c in df.columns if c not in ("Label", "is_attack")]
    for col in feature_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.replace([np.inf, -np.inf], np.nan)
    df = df.dropna()
    df = df.drop_duplicates()
    return df.reset_index(drop=True)


def filter_rare_labels(df: pd.DataFrame, min_count: int | None = None) -> pd.DataFrame:
    """Remove attack families with too few samples for reliable stratified splits."""
    cfg = load_config()
    min_count = cfg["data"].get("min_class_count", 50) if min_count is None else min_count
    counts = df["Label"].value_counts()
    keep = counts[counts >= min_count].index
    dropped = counts[counts < min_count]
    if len(dropped):
        print(f"Dropping rare labels (<{min_count}): {dropped.to_dict()}")
    return df[df["Label"].isin(keep)].reset_index(drop=True)


def get_feature_columns(df: pd.DataFrame) -> list[str]:
    return [c for c in df.columns if c not in ("Label", "is_attack")]


def split_dataset(
    df: pd.DataFrame,
    test_size: float | None = None,
    val_size: float | None = None,
    random_state: int | None = None,
) -> dict[str, pd.DataFrame]:
    """Stratified train / validation / test split on attack family labels."""
    cfg = load_config()
    test_size = cfg["data"]["test_size"] if test_size is None else test_size
    val_size = cfg["data"]["val_size"] if val_size is None else val_size
    random_state = cfg["data"]["random_state"] if random_state is None else random_state

    train_val, test = train_test_split(
        df,
        test_size=test_size,
        random_state=random_state,
        stratify=df["Label"],
    )
    relative_val = val_size / (1.0 - test_size)
    train, val = train_test_split(
        train_val,
        test_size=relative_val,
        random_state=random_state,
        stratify=train_val["Label"],
    )
    return {"train": train.reset_index(drop=True), "val": val.reset_index(drop=True), "test": test.reset_index(drop=True)}


def summarize_labels(df: pd.DataFrame) -> pd.DataFrame:
    counts = df["Label"].value_counts().rename("count")
    pct = (df["Label"].value_counts(normalize=True) * 100).round(2).rename("percent")
    return pd.concat([counts, pct], axis=1)


def save_processed(splits: dict[str, pd.DataFrame], out_dir: Path | None = None) -> Path:
    cfg = load_config()
    out = out_dir or resolve_path(cfg["data"]["processed_dir"])
    out.mkdir(parents=True, exist_ok=True)
    for name, frame in splits.items():
        frame.to_parquet(out / f"{name}.parquet", index=False)
    # Also save a compact metadata summary
    summary = {
        "n_train": len(splits["train"]),
        "n_val": len(splits["val"]),
        "n_test": len(splits["test"]),
        "labels": splits["train"]["Label"].value_counts().to_dict(),
        "features": get_feature_columns(splits["train"]),
    }
    pd.Series(summary).to_json(out / "meta.json")
    return out


def load_processed(split: str = "train", processed_dir: Path | None = None) -> pd.DataFrame:
    cfg = load_config()
    directory = processed_dir or resolve_path(cfg["data"]["processed_dir"])
    path = directory / f"{split}.parquet"
    if not path.exists():
        raise FileNotFoundError(f"Processed split not found: {path}. Run scripts/01_prepare_data.py first.")
    return pd.read_parquet(path)
