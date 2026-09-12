# Implementation status (honest inventory)

Last updated after **final freeze**: Stage-2 retrain (attack-only multiclass), deterministic simulation time, Research Results page, artifact consistency tests.

## Freeze package

- Multiclass `classes_` / `attack_label_encoder`: **Bot, BruteForce, DDoS, DoS, PortScan, WebAttack** — **no BENIGN**
- Binary best: **decision_tree**; Multiclass best: **random_forest**
- Operating threshold **0.85**, uncertainty **[0.10, 0.95]** (regenerated after retrain)
- Calibration remains **disabled** (prior research decision)
- Simulation uses **deterministic `simulation_time`** (not wall-clock)
- Research Results UI + experiment conclusions panels
- Artifact consistency + SHAP alignment + golden-path E2E tests

## Partially / optional

- Browser Playwright journey (API golden-path already covers the loop)
- CSE-CIC-IDS2018 external metrics require compatible CSVs

## Not implemented (do not claim)

- Live packet capture / auto-mitigation / OAuth SSO

## Academic wording

Prefer: **ML-based intrusion detection prototype**, **controlled attack–defense simulation**, **decision-support recommendations**.  
For drift: state that **no feature exceeded PSI ≥ 0.2 on the train→IID test split** — not “there is no data drift.”
