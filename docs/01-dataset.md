# Dataset module

**Path:** `ml/preprocessing/dataset.py`  
**Script:** `scripts/01_prepare_data.py`  
**Source:** `MachineLearningCVE/*.csv` (CICIDS2017)

## Pipeline

1. Load CSVs (optional `sample_frac` for faster iteration)
2. Strip column whitespace
3. Drop leakage-prone columns (`Flow ID`, IPs, `Timestamp`, …)
4. Coerce numerics; replace ±Inf with NaN; drop NaN/duplicates
5. Normalize labels into families: `BENIGN`, `DoS`, `DDoS`, `PortScan`, `BruteForce`, `WebAttack`, `Bot`, `Infiltration`, `Heartbleed`
6. Add `is_attack` binary flag
7. Stratified train / val / test → `data/processed/*.parquet`

## Why MachineLearningCVE?

It is the flow-feature export designed for ML (≈78 numeric features + Label). `TrafficLabelling` is retained for reference but not used by the default pipeline.

## Config knobs (`config.yaml`)

- `data.sample_frac` — set `1.0` for full-dataset experiments (default)
- `data.min_class_count` — drop families with fewer rows (default 50)
- `data.test_size` / `data.val_size`
- `data.drop_columns`
