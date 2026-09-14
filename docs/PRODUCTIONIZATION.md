# Aegis IDS — Productionization Roadmap

**Immutable research baseline:** tag `v1.1-research`.  
**Working branch:** `productionization`.

## Phase status

| Phase | Focus | Status |
|-------|--------|--------|
| P0–P9 | Baseline → … → failure recovery | ✅ |
| **P10** | Generalization | ✅ Complete |
| P11 | Empirical mitigation | Next |
| P12 | Final security validation | — |

## P10 deliverables

- Consolidated report: `docs/GENERALIZATION.md` + `models/trained_models/generalization_report.json` (EXP-017)
- IID vs Friday temporal vs Mon–Thu comparison with **explicit degradation** (Δ = IID − slice)
- Class-wise Friday family table (present: Bot/DDoS/PortScan; absent: BruteForce/DoS/WebAttack)
- Temporal multiclass confusion (diagonal-only in this freeze) + honest non-claims
- IID PSI wording preserved; complementary **train→Friday** PSI (2 features ≥ 0.2)
- External dataset: **future work** (CSE-CIC-IDS2018 not present)
- Research metrics ≠ automatic PCAP-pipeline inheritance; no zero-day claim; no holdout tuning
- Suite: `tests/test_productionization_p10_generalization.py`
- Scripts: `scripts/25_temporal_holdout_eval.py`, `scripts/41_generalization_report.py`

**Completion criterion:** temporal performance + limitations are answerable without relying only on the IID test score — without optimizing the frozen models on the holdout.

## P9 deliverables (prior)

- Startup reclaim, failure matrix, backup/restore drill — see `docs/FAILURE_RECOVERY.md`
