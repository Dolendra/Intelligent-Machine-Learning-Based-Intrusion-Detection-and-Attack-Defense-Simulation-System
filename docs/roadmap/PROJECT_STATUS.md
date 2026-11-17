# Project status

**As of 2026-11-18. Source:** the Phase 0 audit (`docs/research/FULL_REPOSITORY_AUDIT.md` and its companion documents).

## Status labels

| Label | Meaning |
|---|---|
| IMPLEMENTED AND VERIFIED | Implemented; behaviour checked by tests or probes, and no open High finding |
| IMPLEMENTED BUT NOT FULLY VERIFIED | Implemented, but it has open findings or untested paths |
| PARTIALLY IMPLEMENTED | Some parts exist; important parts are missing or broken |
| PROPOSED | Designed or documented only |
| MISSING | Needed, but neither built nor designed |

## Snapshot

| Area | Status | Key evidence |
|---|---|---|
| Frozen v1.1 baseline (DT @ 0.85 + attack-only RF) | IMPLEMENTED AND VERIFIED (artifacts) / **claims incorrect** | Files are byte-identical to the tag on all 4 branches. Reported metrics are mislabelled (ML-1), minority families collapse at 0.85 (ML-2), and the temporal claim is contaminated (ML-3). |
| Aegis-OSR open-set gate (research) | IMPLEMENTED AND VERIFIED (in-distribution) | LOAFO 0.706 vs 0.490, leakage-free, exact regression gate. Under shift, fixed fusion is not justified (RES-3, RES-4). |
| Aegis-OSR gate served in the app | IMPLEMENTED BUT NOT FULLY VERIFIED | Matches research at 0.99996 parity. But the `union` policy raises the benign incident rate about 9× (ML-4), failures are silent (ARCH-10, ML-22), and risk is shown as 0 (ARCH-2). |
| Research publication pipeline (generated numbers, both papers) | IMPLEMENTED AND VERIFIED (traceability) / **claims need correction** | Every number traces to an artifact. Overclaims are listed under RES-1, RES-3, RES-4, RES-11. Decision E (sentence replacement) is pending. |
| R3 benchmark (runner, model registry, leakage checker, score dumps) | PARTIALLY IMPLEMENTED | Tuning is not implemented (RES-10). Ties bias the arms (RES-2). There is no temporal protocol in the runner. |
| Application security (auth, RBAC, limits) | IMPLEMENTED BUT NOT FULLY VERIFIED | RBAC mapping is correct when auth is on. But there is no effective authentication in any documented configuration (SEC-1/2/3), and the body limit can be bypassed (SEC-4). |
| Observability (logs, metrics, readiness) | PARTIALLY IMPLEMENTED | Startup silences the loggers (SEC-5 / ARCH-3). Readiness ignores the gate (ARCH-10). |
| Controlled response (approval gate) | IMPLEMENTED BUT NOT FULLY VERIFIED | No real-network path exists (verified). But VERIFIED status is not persisted (ARCH-5), the audit trail can be purged (SEC-6), there is no four-eyes control (SEC-24), and actions never expire at runtime (ARCH-11). |
| Ingestion (CSV / PCAP / queue) | PARTIALLY IMPLEMENTED | The default CSV mode rejects raw CICIDS2017 files (ARCH-4). The PCAP header mapping is broken (ML-9). The queue discards its detections (ARCH-9). |
| Explainability (SHAP / LIME) | IMPLEMENTED BUT NOT FULLY VERIFIED | SHAP is correct for the model that produces the label. LIME uses the wrong background feature space and the wrong class (ML-6). The alert decision itself is never explained (ML-7). |
| Risk and recommendations | IMPLEMENTED BUT NOT FULLY VERIFIED | Wrong key, so risk shows as 0 (ARCH-2). Gate-only risk uses intensity 0 (ML-5). |
| Cyber Range (trace-driven simulation) | IMPLEMENTED AND VERIFIED (as a simulation) | Real detector verdicts on held-out flows. Correctly labelled as simulation in README. |
| P11 "empirical" mitigation | IMPLEMENTED BUT NOT FULLY VERIFIED / **claim incorrect** | Its results hold by construction (ML-12). |
| Docker deployment | PARTIALLY IMPLEMENTED | The API image cannot start (ARCH-1). WebSockets are not proxied (ARCH-13). nginx caps uploads at 1 MiB (ARCH-24). |
| CI | PARTIALLY IMPLEMENTED | Does not run on the v3 branch. No lint, migration check or container start (ARCH-15). |
| Frontend | IMPLEMENTED BUT NOT FULLY VERIFIED | Typecheck, tests and build pass. Only 3 of 13 pages have tests. |
| Modular research framework (interchangeable modules) | PROPOSED | Exists only on the research side (`r3_models` registry, `clf_factory`). |
| Evidence-reliability estimation / adaptive fusion | PROPOSED | The hypothesis is weak on the discovery data (RESEARCH_ALIGNMENT_REVIEW §5). |
| Independent-dataset validation (LycoS, NF-v3) | MISSING | LycoS is on HOLD pending permission. |

## Phase position

* **Phase 0 (audit):** complete. The documents are delivered for review.
* **Phase 1 (correctness remediation):** planning. See `REMEDIATION_PLAN.md`.

**Waiting for approval:**
* the remediation plan;
* the remediation branch name;
* the deferral of the R3 / GPU campaign until the Phase 4 protocol fixes are done.
