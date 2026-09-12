# Implementation status (honest inventory)

Last updated after final polish (Alembic, decision trace, structured logging).

## Implemented

- Full Aegis loop: prepare → train/select → predict → XAI → risk → rules → recommend → incident → simulate → dashboard
- Research experiments: HPO/calibration, threshold, risk sensitivity, scenario-aware eval, XAI agreement, drift, cross-dataset scoring (when data present)
- Incident intelligence: lifecycle, events, dedup, escalation, campaigns, decision trace
- Simulation: per-attack modules, dynamic metrics, config/replay, before/after
- Engineering: vectorized batch, strict CSV, optional rate-limit/API-key, structured request logs, Alembic migrations, Vitest, CI (pytest + frontend + docker build)

## Partially implemented

- External CSE-CIC-IDS2018 results require placing compatible CSVs
- Intensity reference / calibrated binary need training/script runs
- Compose-up smoke is local (`scripts/19_…`); CI builds images

## Not implemented (do not claim)

- Live packet capture / auto-mitigation / OAuth SSO
- Guaranteed external-dataset metrics without data on disk

## Academic wording

Prefer: **ML-based intrusion detection prototype**, **controlled attack–defense simulation**, **decision-support recommendations**.
