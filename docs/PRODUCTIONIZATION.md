# Aegis IDS — Productionization Roadmap

**Immutable research baseline:** tag `v1.1-research` (Decision Tree @ 0.85 + Random Forest attack-only).  
**Working branch:** `productionization` (extends `main`; never rewrite freeze artifacts under `models/trained_models/`).

## Positioning

| Claim | OK? |
|-------|-----|
| Submission-ready / productionized **IDS prototype** | ✅ |
| Live enterprise SOC / guaranteed zero-day / auto-block | ❌ |

Wording: **“productionized IDS prototype”** or **“submission-ready IDS prototype”** — not “production-ready IDS.”

## Phase status

| Phase | Focus | Status |
|-------|--------|--------|
| **P0** | Freeze `v1.1-research` | ✅ Done |
| **P1** | Real PCAP → flow → frozen DT/RF | ✅ Complete |
| **P2** | Defense dry-run + approval gate | ✅ Complete (this branch) |
| **P3** | Controlled adapter + verify + rollback | Pending (next) |
| **P4** | Reliability / load / DR | Partial metrics; expand later |
| **P5** | External-dataset generalization | Future work (need real dataset) |
| **P6** | Empirical mitigation evidence | Future work (controlled lab) |

## P1 deliverables

1. Harden `POST /api/ingest/pcap` (size / magic / extension validation)
2. Structured ingest audit events
3. Detection UI PCAP upload + queue PCAP
4. `POST /api/ingest/queue/submit-pcap` → same detect queue as CSV
5. CI fixtures under `tests/fixtures/pcap/`
6. Honest **501** without `cicflowmeter`

## P2 deliverables

```text
Detection → risk → recommendation → propose → DRY_RUN → approve/reject → audit
```

Abstract actions: `MONITOR` | `RATE_LIMIT` | `BLOCK_SOURCE` | `ISOLATE_HOST` | `ESCALATE`

| Item | Detail |
|------|--------|
| Propose | `POST /api/response/actions/propose` (or `/api/incidents/{id}/response/propose`) |
| Dry-run | Default mode; never invokes live adapters |
| Approve / Reject | Human gate; reject ⇒ no execution |
| Lifecycle | PROPOSED → APPROVED/REJECTED → EXECUTING → SUCCEEDED → VERIFIED |
| RBAC seed | `write_response` (propose) vs `approve_response` (responder/admin) |
| UI | Incident detail: Propose / Dry run / Approve / Reject |
| Live firewall | **Not implemented** (stub raises `LiveAdapterForbiddenError`) |

## Safety rules

- Do not retrain or overwrite `models/trained_models/*` as part of P1–P4
- Do not claim live NIC capture until that mode is implemented and tested
- Dry-run before any real firewall/EDR action (P2+; live adapters deferred to P3+)
- Recommendations remain advisory until an explicit approval gate exists
