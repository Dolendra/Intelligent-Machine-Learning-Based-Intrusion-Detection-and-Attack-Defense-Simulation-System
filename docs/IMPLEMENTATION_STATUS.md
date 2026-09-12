# Implementation status (honest inventory)

Last updated after submission polish (README dataset honesty, DEMO_MODE batch gate, confidence-band wording, temporal holdout, requirements-lock).

## Freeze + polish

- Stage-2 attack-only multiclass (no BENIGN); Decision Tree + Random Forest
- Threshold **0.85**, confidence band **[0.10, 0.95]** — UI distinguishes attack threshold vs review band
- Calibration disabled (research decision)
- README clarifies raw CICIDS2017 is **not** in Git
- `/predict`, `/predict/batch`, `/predict/batch/csv` (and explain) honor `allow_missing` only under `DEMO_MODE`
- Simulation disclaimer: defense effectiveness = **assumptions**, not measured rates
- Temporal/day-aware holdout: `scripts/25_temporal_holdout_eval.py` → `temporal_holdout_report.json`
- `requirements-lock.txt` pins freeze environment versions
- Experiment index expanded through EXP-016

## Academic wording reminders

- Report **IID stratified** metrics separately from **temporal/Friday holdout** metrics
- Drift: no feature exceeded PSI ≥ 0.2 on train→IID test — not “no drift exists”
- docker-compose uses `DEMO_MODE=true` for demos only

## Optional leftovers

- Playwright browser journeys
- CSE-CIC-IDS2018 external validation (needs compatible CSVs)

## Not implemented (do not claim)

- Live packet capture / auto-mitigation / OAuth SSO
