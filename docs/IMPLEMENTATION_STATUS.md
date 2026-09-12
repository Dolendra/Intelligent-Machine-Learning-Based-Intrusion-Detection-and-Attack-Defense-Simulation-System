# Implementation status (honest inventory)

Last updated after research-finalization: threshold/calibration conclusions, drift artifact, golden-path E2E.

## Implemented

### Correctness & product loop (Phases 1–4)
- Attack-only multiclass, SHAP shapes, severity bands, explicit `source_ref` dedup/campaigns
- Evidence-based operating threshold + uncertainty bands (`threshold_operating_point.json`)
- SOC UI, simulation latencies/series/campaign sim, `/api/ready`, non-root Docker, request IDs

### Research finalization
- **Threshold decision:** operating **0.30**, uncertainty **[0.10, 0.45]** (val sweep; see `docs/experiments/CALIBRATION_AND_THRESHOLD.md`)
- **Calibration decision:** **disabled** — sample isotonic worsened Brier and reduced recall
- **Risk sensitivity:** severity labels stable across A/B/C weight configs
- **Drift:** train→test PSI report (`drift_report.json`); 0 features flagged ≥0.2
- Error analysis + experiment index artifacts refreshed

### Phase-5 Model Lab
- Global/attack importance, counterfactuals, health/drift/experiments UI

### Integration test
- Golden-path API E2E: demo → predict → explain → counterfactual → incident → simulate → recover

## Partially implemented

- Stage-2 **retrain** still recommended so production multiclass joblibs match attack-only encoder semantics from current training code
- External CSE-CIC-IDS2018 needs compatible CSVs for official cross-dataset metrics
- Browser Playwright/Cypress suite (API golden-path covers the loop server-side)

## Not implemented (do not claim)

- Live packet capture / auto-mitigation / OAuth SSO

## Academic wording

Prefer: **ML-based intrusion detection prototype**, **controlled attack–defense simulation**, **decision-support recommendations**.
