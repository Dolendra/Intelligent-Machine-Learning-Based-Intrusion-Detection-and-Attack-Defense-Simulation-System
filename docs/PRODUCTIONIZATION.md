# Aegis IDS — Productionization Roadmap

**Immutable research baseline:** tag `v1.1-research`.  
**Working branch:** `productionization`.

## Phase status

| Phase | Focus | Status |
|-------|--------|--------|
| P0–P5 | Baseline → PCAP → response → adapters → auth → API security | ✅ |
| **P6** | Persistence | ✅ Complete |
| P7 | Observability | Next |

## P6 deliverables

- Alembic migration `002_p6_persistence`: `users`, `response_actions`, `response_audit_events`, `security_audit_events`, `model_version_refs`
- Response actions + append-only audit survive restarts (DB-backed store)
- Atomic status claim prevents duplicate approve/reject under concurrency
- Users directory durable (seed-on-empty); model artifact path refs for frozen baseline
- Incidents, incident events, simulations, `campaign_id` already durable (unchanged)
- Detection/alert history = `Incident` (+ `IncidentEvent`) rows
- Retention policy documented in `config.yaml` / `database.retention` (audit long; simulations shorter; PCAP filesystem TTL)
- Restart / concurrency suite: `tests/test_productionization_p6_persistence.py`
- Explicitly ephemeral: ingest queue, WebSocket hub, rate-limit/metrics buffers, test-adapter controls

**Completion criterion:** propose → dry-run → approve → execute/verify → audit, then restart — records and states remain correct; concurrent duplicate approve yields one success.

Backup automation / full DR is **P9**. ML artifacts untouched.
