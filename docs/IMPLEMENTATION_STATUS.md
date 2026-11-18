# Implementation status (honest inventory)

Last updated after submission polish (README dataset honesty, DEMO_MODE batch gate, confidence-band wording, temporal holdout, requirements-lock).

## Freeze + polish

- Stage-2 attack-only multiclass (no BENIGN); Decision Tree + Random Forest
- Threshold **0.85**, confidence band **[0.10, 0.95]** — UI distinguishes attack threshold vs review band
- Calibration disabled (research decision)
- README clarifies raw CICIDS2017 is **not** in Git
- `/predict`, `/predict/batch`, `/predict/batch/csv` (and explain) honor `allow_missing` only under `DEMO_MODE`
- Simulation disclaimer: defense effectiveness = **assumptions**, not measured rates
- ~~Temporal/day-aware holdout: `scripts/25_temporal_holdout_eval.py` → `temporal_holdout_report.json`~~ **Superseded
  (contaminated, ML-3):** script 25 re-scored rows the model trained on (~70 % of Friday rows). Use the research
  track's day-ordered protocol (`docs/research/RESULTS.md`) for any temporal claim.
- `requirements-lock.txt` pins freeze environment versions
- Experiment index expanded through EXP-016

## Academic wording reminders

- Report **IID stratified** metrics with the threshold they were computed at: the historical test figures are @ 0.5;
  deployed @ 0.85 figures are in `research_artifacts/v11_reeval/` (ML-1, ML-2). Do not cite the script-25 Friday
  figures (superseded).
- Drift: no feature exceeded PSI ≥ 0.2 on train→IID test — not “no drift exists”
- docker-compose uses `DEMO_MODE=true` for demos only

## v3 additions (branch `v3-openset-research`)

- **Aegis-OSR** open-set detector (`research/`): Fisher fusion of supervised + kNN benign-novelty
  evidence, split-conformal benign-FPR control, Mondrian family attribution
- Protocols: leave-one-family-out, **true** temporal split (replaces the leaky script-25 slice for
  temporal claims), CICIDS2017 → CSE-CIC-IDS2018; 5 seeds, CIs, Wilcoxon tests
- Label-light recalibration under shift (no retraining)
- CSE-CIC-IDS2018 external validation of the **frozen** v1.1 models (EXP-009 completed, script 54)
- Production **Zero-Day Gate** (advisory `zero_day` field on predictions; v1.1 verdict unchanged)
- Live Traffic Monitor (`/api/ws/live`, replay of held-out flows), Zero-Day Lab, Research Lab UI
- UI redesign: real charts, light/dark theme, command palette, login page, accessibility fixes
- Performance: `load_config()` now caches parsed YAML (per-flow risk scoring re-parsed it every call)

## Optional leftovers

- Playwright browser journeys

## Not implemented (do not claim)

- Live packet capture / auto-mitigation / OAuth SSO
- The Live Traffic Monitor **replays recorded dataset flows**; it is not packet capture
- No claim that the Zero-Day Gate detects every novel attack (Bot / WebAttack-like traffic remains hard)
