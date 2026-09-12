# Implementation status (honest inventory)

Last updated after polish batch (scenario split, drift, cross-dataset scoring, optional API auth).

## Implemented (including recent review items)

- Dual feature selectors; prediction validation; certainty bands
- Multi-objective selection; threshold/risk/XAI/scenario-aware/drift experiment scripts
- Percentile intensity; rule engine; asset inventory; campaigns + severity escalation
- Dynamic simulation with **per-attack scenario modules** (`simulation/scenarios/*.py`)
- Incident lifecycle, events, dedup; Model/Incident UI; sim config/replay
- Cross-dataset script scores when compatible external CSVs + models exist (else honest skip)
- Optional API rate limit + **API-key auth** (both off by default)
- Vectorized batch; strict CSV; Vitest; CI docker compose build
- Docker healthchecks; compose smoke script

## Partially implemented

- Production dual-selector/calibrated artifacts need retrain / script 14
- Intensity reference requires training run (or falls back to 1e5 scale)
- External CSE-CIC-IDS2018 eval requires placing compatible CSVs under configured dir
- Full compose-up smoke is local/script (CI builds images)
- Model drift / auto-promote is recommendation-only (`20_data_drift_report.py`)

## Not implemented (do not claim)

- Live packet capture / auto-mitigation
- Full Optuna on entire CICIDS; guaranteed external-dataset results without data
- Alembic migrations; production SSO/OAuth

## Academic wording

Prefer: **ML-based intrusion detection prototype**, **controlled attack–defense simulation**, **decision-support recommendations**.
