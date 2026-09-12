# Implementation status (honest inventory)

Last updated after research/ops batch (scenario eval, campaigns, Vitest, Docker CI).

## Implemented (including recent review items)

- Dual feature selectors; prediction validation; certainty bands
- Multi-objective binary model selection; threshold/risk/XAI experiment scripts
- Percentile intensity; rule engine; asset inventory
- Dynamic simulation + config/replay + latency metrics
- Incident lifecycle, events, dedup, **severity escalation**, **campaign correlation**
- Scenario-aware evaluation script (`18_…`) — IID / traffic regimes / attack slices
- Optional API rate limiting (off by default)
- Vectorized batch; strict CSV; Model/Incident UI
- Frontend Vitest smoke tests; CI docker compose build
- Docker healthchecks; compose smoke script (`19_…`)

## Partially implemented

- Production dual-selector/calibrated artifacts need retrain / script 14
- Intensity reference requires training run (or falls back to 1e5 scale)
- Scenario modules still consolidated in `behaviors.py`
- Cross-dataset scoring awaits external CSE-CIC-IDS2018 data (`12_…` scaffold)
- Full docker compose up smoke is local/script (CI builds images)

## Not implemented (do not claim)

- Live packet capture / auto-mitigation
- Full Optuna on entire CICIDS; completed external-dataset eval
- Alembic migrations; production auth (beyond optional rate limit)

## Academic wording

Prefer: **ML-based intrusion detection prototype**, **controlled attack–defense simulation**, **decision-support recommendations**.
