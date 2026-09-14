# Aegis IDS — Security Model

## System type

Aegis is a **security-validated intrusion-detection prototype**, not an enterprise SOC platform and not an automatic network defender.

Primary trust boundaries:

```text
Client / UI
    ↓  (auth optional in research; enforced when enabled)
API gateway (limits, CORS, headers, RBAC)
    ↓
Detect / risk / recommend  →  frozen ML artifacts
    ↓
Response workflow (propose → dry-run → approve → execute → verify → rollback)
    ↓
Adapters: DRY_RUN | CONTROLLED (TestNetworkAdapter) | LIVE (forbidden)
```

---

## Roles (server-enforced)

| Role | Propose / dry-run | Approve / rollback | Admin |
|------|-------------------|--------------------|-------|
| viewer | no | no | no |
| analyst | yes | no | no |
| responder | yes | yes | no |
| admin | yes | yes | yes |

Role is bound in the HMAC bearer token (or server-configured API key role). Clients cannot escalate via forged `actor` fields or role headers when `allow_role_header` is false.

---

## Response safety model

| Mode | Effect |
|------|--------|
| `DRY_RUN` | Preview only; `live_network_change=false`; no TestNetworkAdapter state |
| `CONTROLLED` | In-memory test control plane only |
| `LIVE` | Rejected at propose / adapter layer |

Mandatory human approval before execute. Verification failure triggers rollback. Startup reclaim marks stale `EXECUTING` / orphan `APPROVED` as `FAILED` with **`auto_reexecute: false`**.

---

## Data & audit

- Incidents, response actions, users: durable (P6)
- Response audit + security events: append-only evidence
- Ingest queue / WS hub / rate-limit buffers: ephemeral by design

---

## ML trust

- Artifacts frozen at `v1.1-research` (hash-checked in P12)
- Missing/invalid inputs fail closed — no fabricated success
- Batch predict capped at 500 flows
- Research IID metrics are **not** live-traffic guarantees (see P10)

---

## Simulation vs empirical

| Track | Meaning |
|-------|---------|
| Simulation | Visualization; `defense_effectiveness` are **assumptions** |
| P11 empirical | Measured outcomes on CONTROLLED lab plane |

Neither path may invoke a real firewall, EDR, NIC, or router.

---

## Explicit non-goals

- Live firewall / EDR enforcement
- Uncontrolled packet manipulation
- Automatic response without approval
- Zero-day guarantees
- Enterprise SOC / SLA claims
