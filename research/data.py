"""Research data layer.

Unlike ``ml/preprocessing`` (which feeds the frozen v1.1 models), this loader keeps:

* ``day``        — capture day parsed from the CSV filename (enables a *true* temporal split)
* ``fine_label`` — the original attack name (e.g. ``DoS Hulk``)
* ``family``     — normalized attack family, including the rare ``Infiltration`` / ``Heartbleed``

Both datasets are mapped onto the CICIDS2017 MachineLearningCVE feature schema so that a
model trained on one can be scored on the other.
"""
from __future__ import annotations

import re
from pathlib import Path

import numpy as np
import pandas as pd

from ids_config import ROOT
from ingestion.normalize import normalize_flow_frame
from ml.preprocessing.dataset import normalize_labels

CIC2017_DIR = ROOT / "MachineLearningCVE"
CIC2018_DIR = ROOT / "CSE-CIC-IDS2018"
CACHE_DIR = ROOT / "research_artifacts" / "cache"
ARTIFACT_DIR = ROOT / "research_artifacts"

META_COLS = ["day", "fine_label", "family", "is_attack", "dataset", "seq"]
DAYS_2017 = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
# Chronological order of the CICIDS2017 capture files within a day (CICFlowMeter writes flows
# roughly in completion order, so (file rank, row index) approximates capture time).
_FILE_ORDER_2017 = ["morning", "afternoon-portscan", "afternoon-ddos", "afternoon-infilteration"]

# Columns that are identifiers, timestamps, or exact duplicates of another feature.
_NON_FEATURES = {
    "Flow ID", "Source IP", "Destination IP", "Source Port", "Timestamp",
    "Src IP", "Dst IP", "Src Port", "Protocol", "Label",
}
_DUPLICATE_FEATURES = {"Fwd Header Length.1"}

# CSE-CIC-IDS2018 label → family (aligned with CICIDS2017 families).
_LABEL_MAP_2018 = {
    "benign": "BENIGN",
    "bot": "Bot",
    "dos attacks-goldeneye": "DoS",
    "dos attacks-slowloris": "DoS",
    "dos attacks-slowhttptest": "DoS",
    "dos attacks-hulk": "DoS",
    "ddos attacks-loic-http": "DDoS",
    "ddos attack-loic-udp": "DDoS",
    "ddos attack-hoic": "DDoS",
    "ftp-bruteforce": "BruteForce",
    "ssh-bruteforce": "BruteForce",
    "brute force -web": "WebAttack",
    "brute force -xss": "WebAttack",
    "sql injection": "WebAttack",
    "infilteration": "Infiltration",
    "infiltration": "Infiltration",
}


def _day_2017(path: Path) -> str:
    name = path.name.lower()
    for day in DAYS_2017:
        if name.startswith(day.lower()):
            return day
    return "Unknown"


def _seq_base_2017(path: Path) -> int:
    name = path.name.lower()
    for rank, tag in enumerate(_FILE_ORDER_2017):
        if tag in name:
            return rank * 10_000_000
    return 0


def _day_2018(path: Path) -> str:
    m = re.search(r"(\d{2})-(\d{2})-(\d{4})", path.name)
    return f"{m.group(3)}-{m.group(2)}-{m.group(1)}" if m else path.stem


def _finalize(df: pd.DataFrame, feature_cols: list[str]) -> pd.DataFrame:
    """Numeric coercion, Inf/NaN removal, de-duplication, float32 features."""
    for col in feature_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df[feature_cols] = df[feature_cols].replace([np.inf, -np.inf], np.nan)
    df = df.dropna(subset=feature_cols)
    df = df.drop_duplicates(subset=feature_cols + ["fine_label"])
    df[feature_cols] = df[feature_cols].astype(np.float32)
    df["is_attack"] = (df["family"] != "BENIGN").astype(np.int8)
    if "seq" not in df.columns:
        df["seq"] = np.arange(len(df), dtype=np.int64)
    for col in ("day", "fine_label", "family", "dataset"):
        df[col] = df[col].astype("category")
    return df.reset_index(drop=True)


def feature_columns(df: pd.DataFrame) -> list[str]:
    return [c for c in df.columns if c not in META_COLS]


# --------------------------------------------------------------------------- CICIDS2017
def build_cic2017(raw_dir: Path = CIC2017_DIR) -> pd.DataFrame:
    files = sorted(raw_dir.glob("*.csv"))
    if not files:
        raise FileNotFoundError(f"No CICIDS2017 CSVs in {raw_dir}")
    frames = []
    for path in files:
        df = pd.read_csv(path, low_memory=False, encoding="latin-1")
        df.columns = [c.strip() for c in df.columns]
        raw = df["Label"].astype(str).str.strip()
        # latin-1 decoding of the en-dash in "Web Attack – XSS"
        raw = raw.str.replace("\x96", "-", regex=False).str.replace("�", "-", regex=False)
        df = df.drop(columns=[c for c in df.columns if c in _NON_FEATURES | _DUPLICATE_FEATURES])
        df["fine_label"] = raw.str.replace(r"\s+-\s+", " - ", regex=True)
        df["family"] = normalize_labels(raw).values
        df["day"] = _day_2017(path)
        df["dataset"] = "CICIDS2017"
        df["seq"] = _seq_base_2017(path) + np.arange(len(df), dtype=np.int64)
        frames.append(df)
    out = pd.concat(frames, ignore_index=True)
    return _finalize(out, [c for c in out.columns if c not in META_COLS])


def load_cic2017(*, rebuild: bool = False) -> pd.DataFrame:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache = CACHE_DIR / "cic2017.parquet"
    if cache.exists() and not rebuild:
        return pd.read_parquet(cache)
    df = build_cic2017()
    df.to_parquet(cache, index=False)
    return df


# --------------------------------------------------------------------------- CSE-CIC-IDS2018
def _map_label_2018(series: pd.Series) -> pd.Series:
    key = series.astype(str).str.strip().str.lower()
    return key.map(_LABEL_MAP_2018).fillna("Other")


def build_cic2018(
    raw_dir: Path = CIC2018_DIR,
    *,
    target_features: list[str],
    benign_frac: float = 0.05,
    cap_per_label: int = 150_000,
    chunksize: int = 500_000,
    seed: int = 42,
    version: int = 1,
) -> pd.DataFrame:
    """Stream the (very large) 2018 CSVs, keep all attacks up to a per-label cap and a
    uniform ``benign_frac`` sample of benign flows, mapped to the 2017 schema."""
    files = sorted(raw_dir.glob("*.csv"))
    if not files:
        raise FileNotFoundError(f"No CSE-CIC-IDS2018 CSVs in {raw_dir}")
    rng = np.random.default_rng(seed)
    kept: dict[str, list[pd.DataFrame]] = {}
    counts: dict[str, int] = {}
    for path in files:
        day = _day_2018(path)
        offset = 0
        for chunk in pd.read_csv(path, chunksize=chunksize, low_memory=False):
            row_seq = offset + np.arange(len(chunk), dtype=np.int64)
            offset += len(chunk)
            chunk.columns = [c.strip() for c in chunk.columns]
            not_header = (chunk["Label"].astype(str).str.strip() != "Label").to_numpy()  # repeated headers
            chunk, row_seq = chunk[not_header], row_seq[not_header]
            fine = chunk["Label"].astype(str).str.strip()
            fam = _map_label_2018(fine)
            benign = (fam == "BENIGN").to_numpy()
            take = ~benign | (rng.random(len(chunk)) < benign_frac)
            chunk = normalize_flow_frame(chunk.loc[take])
            chunk["fine_label"] = fine[take].values
            chunk["family"] = fam[take].values
            chunk["day"] = day
            chunk["dataset"] = "CSE-CIC-IDS2018"
            chunk["seq"] = row_seq[take]
            missing = [c for c in target_features if c not in chunk.columns]
            for c in missing:
                chunk[c] = np.nan
            chunk = chunk[target_features + ["fine_label", "family", "day", "dataset", "seq"]]
            for label, part in chunk.groupby("fine_label", observed=True):
                if version == 1:
                    # v1 (kept for reproducibility of pre-R1b results): one GLOBAL cap per label in
                    # file order. Defect: once "Benign" hit the cap (after 4 of 10 files), later
                    # days kept no benign traffic at all.
                    room = cap_per_label - counts.get(label, 0)
                    if room <= 0:
                        continue
                    part = part.iloc[:room]
                    kept.setdefault(label, []).append(part)
                    counts[label] = counts.get(label, 0) + len(part)
                else:
                    # v2: benign = the uniform benign_frac sample of EVERY day (no further cap);
                    # attacks capped per (day, label) by a seeded random subsample, not file order.
                    key = f"{day}|{label}"
                    if label.lower() != "benign":
                        part = part.assign(__r=rng.random(len(part)))
                        prev = kept.get(key)
                        part = part if prev is None else pd.concat([prev[0], part])
                        if len(part) > cap_per_label:
                            part = part.nsmallest(cap_per_label, "__r")
                        kept[key] = [part]
                    else:
                        kept.setdefault(key, []).append(part)
    out = pd.concat([p for parts in kept.values() for p in parts], ignore_index=True)
    out = out.drop(columns=["__r"], errors="ignore")
    out = out[out["family"] != "Other"]
    return _finalize(out, target_features)


CIC2018_CACHE = {1: "cic2018_sample.parquet", 2: "cic2018_sample_v2.parquet"}


def load_cic2018(target_features: list[str], *, rebuild: bool = False, version: int = 2, **kwargs) -> pd.DataFrame:
    """CSE-CIC-IDS2018 sample. ``version=2`` (default since R1b) keeps benign traffic for every
    capture day; ``version=1`` reproduces the pre-R1b sample (benign from 4 of 10 days only)."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache = CACHE_DIR / CIC2018_CACHE[version]
    if cache.exists() and not rebuild:
        df = pd.read_parquet(cache)
        if feature_columns(df) == list(target_features):
            return df
    kw = dict(kwargs)
    if version == 2:
        kw.setdefault("cap_per_label", 100_000)
    df = build_cic2018(target_features=target_features, version=version, **kw)
    df.to_parquet(cache, index=False)
    return df


# --------------------------------------------------------------------------- sampling helpers
def cap_per_family(df: pd.DataFrame, caps: dict[str, int] | int, seed: int) -> pd.DataFrame:
    """Down-sample each family to at most ``caps[family]`` rows (or a single int cap)."""
    parts = []
    for fam, part in df.groupby("family", observed=True):
        cap = caps if isinstance(caps, int) else caps.get(str(fam), len(part))
        parts.append(part.sample(n=cap, random_state=seed) if len(part) > cap else part)
    return pd.concat(parts, ignore_index=True) if parts else df.iloc[:0]


def stratified_split(
    df: pd.DataFrame, fractions: tuple[float, float, float], seed: int
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Per-family random split into (train, val, test) by the given fractions."""
    rng = np.random.default_rng(seed)
    a, b, c = [], [], []
    f_train, f_val, _ = fractions
    for _, part in df.groupby("family", observed=True):
        idx = rng.permutation(len(part))
        n_tr = int(round(f_train * len(part)))
        n_va = int(round(f_val * len(part)))
        a.append(part.iloc[idx[:n_tr]])
        b.append(part.iloc[idx[n_tr:n_tr + n_va]])
        c.append(part.iloc[idx[n_tr + n_va:]])
    return (pd.concat(a, ignore_index=True), pd.concat(b, ignore_index=True), pd.concat(c, ignore_index=True))
