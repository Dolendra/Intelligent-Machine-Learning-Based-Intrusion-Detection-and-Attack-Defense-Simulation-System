# Implementation gaps

**As of 2026-11-18.** Gaps are grouped by type.

* **IDs** refer to the Phase 0 audit documents in `docs/research/`.
* **Status labels** are as in PROJECT_STATUS.md.
* **Priorities** are the remediation tiers in REMEDIATION_PLAN.md.

## 1. Blockers — must be closed before any further research compute or framework work

| # | Gap | IDs | Type | Priority |
|---|---|---|---|---|
| B1 | No effective authentication in any documented configuration | SEC-1, SEC-2, SEC-3 (+SEC-28) | Confirmed defect | P0 |
| B2 | Logging is silenced at startup, so security, error and ingest-audit trails are lost | SEC-5 / ARCH-3, SEC-8 | Confirmed defect | P0 |
| B3 | Risk is read with the wrong key, so the gate-only and live risk shown is 0 | ARCH-2, ML-5 | Confirmed defect | P0 |
| B4 | The gate is silently degraded, and readiness ignores it | ARCH-10, ML-22 | Confirmed defect | P0 |
| B5 | Public claims do not match the evidence: metrics labelled @0.85 were computed at 0.5; minority-family collapse; contaminated temporal result; gate "advisory" but alters the incident rate; P11 "measured"; unconditional FPR guarantee; paper omissions | ML-1, ML-2, ML-3, ML-4, ML-12, RES-1, RES-3, RES-4, RES-11 | Confirmed (claims) | P0 (docs); corrected numbers in new artifacts |
| B6 | Body-size limit can be bypassed | SEC-4 | Confirmed defect | P0 |
| B7 | Response audit trail can be purged | SEC-6 | Confirmed defect | P0 |
| B8 | R3 is not campaign-ready: ties, missing tuning, no temporal protocol, asymmetries | RES-2, RES-10, RES-18 | Confirmed | Phase 4 (protocol); blocks Phase 5 |

## 2. Application correctness gaps

| Gap | IDs | Priority |
|---|---|---|
| Docker API image cannot start | ARCH-1 | P1 |
| Default CSV mode rejects raw dataset CSVs; two parsers | ARCH-4, ML-13 | P1 |
| NaN/Inf/missing-value policy inconsistent; `/predict` returns 500 | ML-8, ML-14 | P1 |
| PCAP extractor header mapping | ML-9 | P1 |
| VERIFIED status not persisted | ARCH-5 | P1 |
| Simulate reopens closed incidents | ARCH-6 | P1 |
| Blocking work inside async handlers | ARCH-7 / SEC-9 | P1 |
| Incident-ID collisions | ARCH-12 | P1 |
| Rate-limit keying behind proxy | SEC-10 | P1 |
| Queue leaks memory and discards detections | ARCH-9 | P2 |
| WebSockets behind nginx; CORS on error responses; nginx body limit | ARCH-13, ARCH-14, ARCH-24, SEC-23 | P2 |
| Actions never expire at runtime; retention never applied | ARCH-11 | P2 |
| Multi-worker safety | ARCH-8 / SEC-25 | P2 (enforce single worker) |

## 3. ML and explainability gaps

| Gap | IDs | Priority |
|---|---|---|
| LIME wrong background and class; alert decision unexplained | ML-6, ML-7 | P2 |
| Destination Port shortcut not measured | ML-10, RES-12 | Phase 4 (ablation) |
| Risk confidence semantics | ML-16 | P2 |
| Threshold display and source drift; certainty-band wording | ML-15, ML-18 | P2 |
| Dead families in decision logic; DDoS plan mismatch | ML-19, ML-23 | P3 |
| Calibration tooling broken (inactive) | ML-17 | P3 |
| sklearn version pin in CI and Docker | ML-21, SEC-22 | P1 |

## 4. Research-methodology gaps (Phase 2 / Phase 4)

| Gap | IDs |
|---|---|
| Matched-FPR comparisons; randomised conformal p-values | RES-2, RES-8, RES-22 |
| Tuning implemented and frozen; temporal protocol in the runner | RES-10 |
| Design-free confirmation flows | RES-6 |
| Family- and day-level uncertainty; calibration-conditional bounds | RES-5, RES-7 |
| Per-day oracle; contamination controls; timestamp order | RES-9, RES-14, RES-15 |
| Tool-level known/unknown split; cross-dataset LOAFO | RES-13 |
| Artifact-guard coverage of scripts 51/52/58/61 | RES-17 |
| Label-conflict counting; Mondrian scope statement; α = 0.001 cells marked n/a | RES-19, RES-20, RES-21 |
| Remaining literature (Springer Mondrian triage, MDPI fusion, F4, F6) | RESEARCH_ALIGNMENT_REVIEW §2 |
| Independent dataset with permission | LycoS HOLD; NF-v3 |

## 5. Engineering and process gaps

| Gap | IDs | Priority |
|---|---|---|
| CI does not cover v3; no lint, migration check or container smoke test | ARCH-15 | P1 |
| No Python linter or type checker configured | §2 of FULL_REPOSITORY_AUDIT | P1 (with CI) |
| Frontend tests cover 3 of 13 pages | ARCH-15 | P2 |
| Untyped API responses; hand-written TypeScript types | ARCH-29 | P3 |
| Oversized modules; duplicated logic; dead code | ARCH-27, ARCH-28, ARCH-30 | P3 |
| Token revocation; key rotation; constant-time comparison; WebSocket token in query string | SEC-11 to SEC-14, SEC-27 | P2 |
| Four-eyes approval and allowlisted targets before any real adapter | SEC-24, SEC-26 | P2 |
| `docs/IMPLEMENTATION_STATUS.md` (main-branch file) still presents the script-25 temporal holdout as valid (line 13) | ML-3 | P0 (docs) |

## 6. Framework gaps (Phase 9; do not start yet)

* **Modular serving interfaces:** detection, open-set, explanation, adaptation, decision. **PROPOSED.**
* **Model registry at serving time.** **MISSING.**
* **Runtime drift / evidence-reliability layer.** **PROPOSED.** Depends on the Phase 6 outcome.
