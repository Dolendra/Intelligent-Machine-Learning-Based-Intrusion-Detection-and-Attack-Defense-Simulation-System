# Architecture status

**As of 2026-11-18.** Detail: `docs/research/ARCHITECTURE_AUDIT.md`. Labels are as in PROJECT_STATUS.md.

## Current architecture (as built)

```
Browser (React 19 SPA, api.ts) ──REST/WS──► nginx (Docker) / Vite proxy (dev)
        │
        ▼
FastAPI app (backend/main.py)
  Middleware, outermost → innermost:
    Logging → Metrics → SecurityHeaders → Auth/RBAC → RateLimit → RequestSize → CORS
  Routers:
    api.py (66 handlers) · v3.py (zero-day, research, /ws/live) · range.py
        │
        ▼
backend/services/pipeline.py (1,200 LOC)
  frozen v1.1 predictor ─► risk/recommendation ─► Zero-Day Gate (research/serving.py)
  ─► detection_policy (union) ─► incidents/campaigns (SQLAlchemy) ─► decision trace
        │
        ├─ ingestion/   (CSV/PCAP normalisation, cicflowmeter subprocess, in-process queue)
        ├─ security/    (auth, rbac, response lifecycle + adapters [no live adapter], risk, rules)
        ├─ explainability/ (SHAP, LIME, counterfactual)
        ├─ simulation/ (legacy demo) · cyberrange/ (trace-driven) · empirical/ (script-only)
        └─ database/ + alembic/ (SQLite default, Postgres optional)
```

## Layer status

| Target layer (roadmap) | Today | Status | Main gaps |
|---|---|---|---|
| L1 Network data intelligence | `ingestion/`, schema JSON, aliases | PARTIALLY IMPLEMENTED | ARCH-4/ML-13 (two CSV parsers); ML-9 (PCAP headers); ML-8 (NaN/Inf policy); ARCH-9 (queue) |
| L2 Intelligent detection | Frozen DT+RF; Aegis-OSR gate | IMPLEMENTED BUT NOT FULLY VERIFIED | Fixed models, no registry at serving (ML-1/2/4) |
| L3 Research intelligence (XAI, uncertainty, drift, reliability) | SHAP/LIME; static drift report | PARTIALLY IMPLEMENTED | ML-6/7; no runtime drift or reliability layer |
| L4 Adaptive decision (fusion, risk, defence selection) | Fixed policy, risk engine, playbooks | PARTIALLY IMPLEMENTED | ARCH-2, ML-5, ML-16, ML-23; adaptation PROPOSED |
| L5 Controlled cyber defence | Response lifecycle, approval, verify/rollback | IMPLEMENTED BUT NOT FULLY VERIFIED | ARCH-5/11/23, SEC-6/24 |
| L6 Cyber range and evaluation | `cyberrange/`, R3 runner | IMPLEMENTED (sim) / PARTIALLY (R3) | ARCH-20; RES-2/10 |
| Cross-cutting: security | Auth/RBAC/limits | IMPLEMENTED BUT NOT FULLY VERIFIED | SEC-1–5 |
| Cross-cutting: observability | Logs, metrics, readiness | PARTIALLY IMPLEMENTED | SEC-5/ARCH-3, ARCH-10, ARCH-22 |
| Cross-cutting: deployment | Docker, compose, nginx | PARTIALLY IMPLEMENTED | ARCH-1/13/24, SEC-23 |

## Structural properties

* **Contracts.** Every UI call maps to a route. Only 2 routes declare response models; TypeScript types are maintained by hand (ARCH-29).
* **Module size.** Three oversized modules: `api.py`, `pipeline.py` and `api.ts` (ARCH-28).
* **Imports.** No top-level import cycles. Domain modules import the web layer lazily (ARCH-28).
* **Duplicated logic** (ARCH-27):
  * the auth-enabled flag is computed in six places;
  * there are two WebSocket auth implementations, two PCAP handlers and two CSV parsers;
  * there are four scenario/replay engines.
* **Scaling.** The design is single-process: the queue, range runs, sim sessions, rate limiter and event hub all hold in-memory state. Running more than one worker is unsafe (ARCH-8).
* **Simulation vs enforcement.** Clean separation in code: no live adapter can be reached. Some documents mislabel this (ML-12).

## Reusable as-is for the future modular framework

* `research/r3_models.py` registry pattern
* `AegisOSR(clf_factory, methods)`
* `research/protocols.py` (splits, leakage checks, score dumps)
* `research/artifact_guard.py`
* `security/response` adapter contract
* `security/detection_policy.py`

## Needs proper interfaces before modularisation (no restructuring yet)

* The predictor loader (hard-coded v1.1 file names).
* Gate loading (singleton, failure cached).
* Explanation selection (which model, which background).
* Risk input contract (typed result; ARCH-2).
* Scenario/replay engines (one shared scorer).
* Ingestion parsing (one parser).
