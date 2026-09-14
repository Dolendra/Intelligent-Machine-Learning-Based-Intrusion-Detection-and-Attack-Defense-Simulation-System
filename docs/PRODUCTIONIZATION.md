# Aegis IDS — Productionization Roadmap

**Immutable research baseline:** tag `v1.1-research`.  
**Working branch:** `productionization`.

## Phase status

| Phase | Focus | Status |
|-------|--------|--------|
| P0–P8 | Baseline → … → performance | ✅ |
| **P9** | Failure recovery / DR | ✅ Complete |
| P10 | Generalization | Next |

## P9 deliverables

- Startup reclaim of stale `EXECUTING` / orphan `APPROVED` → `FAILED` (no auto-replay)
- Failure matrix + recovery states in `docs/FAILURE_RECOVERY.md`
- SQLite backup/restore/verify + disaster drill: `scripts/40_db_backup_restore.py`
- Measured drill RTO (~0.02s local) and drill RPO≈0 (schedule defines ops RPO)
- Suite: `tests/test_productionization_p9_recovery.py`
- `/api/ops/status.recovery` summary

**Completion criterion:** defined component failures fail safely, critical security state is preserved/reclaimed, and restore is tested — with honest non-enterprise limits.
