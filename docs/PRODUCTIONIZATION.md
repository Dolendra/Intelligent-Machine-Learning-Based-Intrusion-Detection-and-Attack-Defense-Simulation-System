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
| **P1** | Real PCAP → flow → frozen DT/RF | ✅ Complete (this branch) |
| **P2** | Defense dry-run + approval gate | Pending (next) |
| **P3** | Auth / RBAC enablement | Scaffolding exists; enable later |
| **P4** | Reliability / load / DR | Partial metrics; expand later |
| **P5** | External-dataset generalization | Future work (need real dataset) |
| **P6** | Empirical mitigation evidence | Future work (controlled lab) |

## P1 deliverables

1. Harden `POST /api/ingest/pcap` (size / magic / extension validation)
2. Structured ingest audit events (request-scoped)
3. Detection UI PCAP upload + queue PCAP
4. `POST /api/ingest/queue/submit-pcap` → **same** in-process detect queue as CSV
5. CI fixtures: `tests/fixtures/pcap/minimal.pcap` + `golden_flows.csv` (mock extract only)
6. Keep **501** when `cicflowmeter` is absent (no fake extraction on the live API)

### Path

```text
PCAP → validation → audit → cicflowmeter → flow CSV → existing queue → frozen DT/RF
```

## Safety rules

- Do not retrain or overwrite `models/trained_models/*` as part of P1–P4
- Do not claim live NIC capture until that mode is implemented and tested
- Dry-run before any real firewall/EDR action (P2+)
- Recommendations remain advisory until an explicit approval gate exists
