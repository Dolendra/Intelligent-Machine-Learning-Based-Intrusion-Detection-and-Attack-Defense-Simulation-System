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
| **P2** | Defense dry-run + approval gate | ✅ Complete |
| **P3** | Adapter + verify + rollback | ✅ Complete (this branch) |
| **P4** | Auth / RBAC enablement | Scaffolding exists; expand next |
| **P5+** | Hardening / persistence / load / DR / generalization | Later |

## P3 deliverables

```text
Propose → Dry-run → Approve → ResponseAdapter.execute → verify → ACTIVE/VERIFIED
                                                    ↘ verify fail → rollback
ACTIVE → expire → rollback cleanup → EXPIRED
```

| Adapter | Role |
|---------|------|
| `dry_run` | Default — no state change |
| `test_network` | CONTROLLED simulated control plane |
| `live_forbidden` | Stub — always raises |

Contract: `validate` / `preview` / `execute` / `verify` / `rollback`

Reversibility: `BLOCK_SOURCE↔UNBLOCK_SOURCE`, `RATE_LIMIT↔REMOVE_RATE_LIMIT`, …; `ESCALATE` marked non-reversible.

## Safety invariants (tested)

- No approval → no execution  
- Dry-run → no real network modification  
- CONTROLLED → simulated only (`live_network_change: false`)  
- LIVE / firewall / EDR → forbidden  
- Verify failure → rollback when reversible  
- Every transition → audit  

## Safety rules

- Do not retrain or overwrite `models/trained_models/*`
- Do not claim live NIC capture or live firewall blocking yet
- Real vendor adapters come only after this contract is proven
