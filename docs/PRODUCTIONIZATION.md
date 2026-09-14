# Aegis IDS — Productionization Roadmap

**Immutable research baseline:** tag `v1.1-research`.  
**Working branch:** `productionization`.

## Phase status

| Phase | Focus | Status |
|-------|--------|--------|
| P0–P10 | Baseline → … → generalization | ✅ |
| **P11** | Empirical mitigation | ✅ Complete |
| P12 | Final security validation | Next |

## P11 deliverables

- Controlled in-process lab: `empirical/controlled_plane.py` gated by `TestNetworkAdapter.traffic_decision`
- Conditions: **no_defense** vs **recommendation_only** vs **controlled_response** (approval → verify → rollback preserved)
- Measured metrics + T0–T8 timeline; mean/median/stdev/min/max/p95 over 10 reps
- EXP-018 (DDoS `BLOCK_SOURCE`), EXP-019 (DoS `RATE_LIMIT`) → `empirical_mitigation_report.json`
- Simulation assumptions **preserved** and reported beside measurements (`docs/EMPIRICAL_MITIGATION.md`)
- No LIVE firewall/EDR; suite `tests/test_productionization_p11_empirical.py`
- Script: `scripts/42_empirical_mitigation_experiment.py`

**Completion criterion:** measurable change with vs without approved CONTROLLED defense — with experimental data, not simulation assumptions alone.

## Prior phases

- P10: `docs/GENERALIZATION.md`
- P9: `docs/FAILURE_RECOVERY.md`
