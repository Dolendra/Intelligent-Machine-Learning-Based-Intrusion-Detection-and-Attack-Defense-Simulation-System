# Aegis IDS — Productionization Roadmap

**Immutable research baseline:** tag `v1.1-research`.  
**Working branch:** `productionization`.

## Phase status

| Phase | Focus | Status |
|-------|--------|--------|
| P0–P7 | Baseline → … → observability | ✅ |
| **P8** | Performance / load | ✅ Complete |
| P9 | Failure recovery / DR | Next |

## P8 deliverables

- Harness: `performance/harness.py` → JSON under `results/performance/`
- Scripts: `30`–`37` prediction / batch / SHAP / API / queue / DB / stages / envelope
- Scenarios: normal, high, saturation (queue-full)
- SHAP vs ML-only comparison; stage breakdown
- Concurrent response approve claim under load
- Docs: `docs/PERFORMANCE.md` + `operating_envelope_latest.json`
- CI: shape-only `tests/test_productionization_p8_performance.py` (no heavy benches)

**Completion criterion:** measured operating envelope with flows/sec, p50/p95, error rate, and saturation behavior — not a vague “scalable” claim. ML artifacts untouched.
