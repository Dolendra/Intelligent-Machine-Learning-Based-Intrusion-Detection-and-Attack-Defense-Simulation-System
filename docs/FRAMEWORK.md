# AEGIS modular framework (roadmap Phases 9–10)

The framework turns the system's parts into **interchangeable modules behind typed interfaces**. The same composition
can be served by the API and swapped in experiments. It wraps the existing, tested components and re-implements no
detection logic, so the default pipeline is decision-identical to the service (`tests/test_framework.py`).

## Module kinds

| Kind | Interface (`framework/interfaces.py`) | Built-in modules | Status |
|---|---|---|---|
| detector | `detect(rows) -> [DetectionOutput]` | `frozen_v11`: frozen Decision Tree (binary, operating threshold) + Random Forest (family) | IMPLEMENTED AND VERIFIED |
| open_set | `assess(rows) -> [OpenSetOutput]` | `aegis_osr_gate`: conformal p-value of Fisher-fused XGB + kNN evidence. `none`: closed-set operation | IMPLEMENTED AND VERIFIED |
| adapter | `adapt(benign_rows) -> AdaptationReport` | `conformal_recalibration`: benign-window recal@W on a private gate copy; never retrains | IMPLEMENTED BUT NOT FULLY VERIFIED (exchangeable-data test only; under shift it re-targets the threshold but does not restore detection) |
| explainer | `explain(row, top_k) -> dict` | `shap`, `lime` | IMPLEMENTED AND VERIFIED (existing engines) |
| policy | `decide(detection, open_set) -> Decision` | `frozen` (default), `gate`, `union`: the shared incident policy | IMPLEMENTED AND VERIFIED |

* **Interfaces are `typing.Protocol`s**, so a module needs no framework base class. `Registry.create` checks the
  interface at runtime and rejects non-conforming modules.
* **Outputs are frozen dataclasses** (`DetectionOutput`, `OpenSetOutput`, `Decision`, `AdaptationReport`).

## Composition

```python
from framework import AegisPipeline
pipe = AegisPipeline.from_config()                       # config.yaml -> framework (the API's pipeline)
pipe = AegisPipeline.build(open_set="none")              # closed-set variant
pipe = AegisPipeline.build(policy="union", adapter="conformal_recalibration")
results = pipe.process(flows)                            # [PipelineResult(detection, open_set, decision)]
```

`config.yaml → framework` selects the active modules. `policy: null` falls back to
`zero_day_gate.incident_policy`, so the framework and the API can never disagree on the policy.

## Integration (Phase 10)

| Surface | What it does |
|---|---|
| `GET /api/framework/modules` | The module catalogue (with status labels) and the active pipeline |
| `POST /api/framework/assess` | Runs flows through a chosen combination (`policy`, `open_set`). **Read-only**: nothing is persisted and no incident is raised. At most 500 flows. |
| `GET /api/research/r3` | Pre-registered R3 verdicts, per-model effects and the reliability study (404 until the analysis exists) |
| Research Lab → **R3 campaign** tab | Shows the above, plus the framework module table |

**End-to-end test** (`tests/test_e2e_integration.py`):
1. A flow goes through `POST /api/predict` and creates an incident.
2. The incident drives a response proposal (dry-run).
3. The same traffic is compared across the three policies through the framework, with the database unchanged.
4. The framework verdict equals the service verdict.

## What the framework does not do

* **No new detector.** The research found no method worth adding (see `docs/research/R3_RESULTS.md`).
* **No automatic adaptation in serving.** The adapter exists for experiments and is off by default (`adapter: null`).
* **No guarantee under shift.** Under distribution shift the conformal bound holds only conditionally on
  exchangeability; recalibration re-targets the threshold but does not restore detection.
