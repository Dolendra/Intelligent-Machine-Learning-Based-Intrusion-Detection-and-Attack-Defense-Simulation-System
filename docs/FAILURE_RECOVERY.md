# Aegis IDS — P9 Failure Recovery / DR

**Branch:** `productionization`  
**Scope:** Controlled failure behavior + tested SQLite backup/restore.  
**Not claimed:** Enterprise multi-region DR, automated offsite replication, or zero-RPO continuous protection.

## Recovery state model

```text
Healthy → Degraded → Failed → Recovering → Healthy
```

| State | Meaning |
|-------|---------|
| Healthy | `/api/ready` true; deps ok |
| Degraded | Optional deps down (e.g. PCAP extractor); core still ready |
| Failed | Required dep down → `503 NOT_READY` or action `FAILED` |
| Recovering | Startup reclaim / restore procedure in progress |
| Healthy | Deps restored; critical security state consistent |

## Failure matrix

| Failure | Detection | System behavior | Recovery | Data loss |
|---------|-----------|-----------------|----------|-----------|
| DB unavailable | Readiness | `503 NOT_READY`; health still liveness-ok | Restore connectivity / restore backup | Since last backup (ops RPO) |
| Model artifact missing/unloadable | Readiness + predict | `NOT_READY`; predict returns model error — **no fake scores** | Restore `models/trained_models` from baseline | None (artifacts immutable) |
| Queue / worker process crash | Queue status / restart | In-process jobs **lost** (ephemeral by design); no silent “success” | Restart API/worker; resubmit | In-flight queue jobs only |
| Queue saturation | Submit error | Reject at `max_jobs` (P8) | Drain / raise capacity | None |
| PCAP invalid / extractor missing | Validation / 501 | Reject + audit; **never invent predictions** | Fix input / install cicflowmeter | None |
| Temp filesystem unusable | Upload / FS check | Ready may fail filesystem; uploads error | Fix permissions/space | Temp files only |
| Adapter execute failure | Action status | `FAILED` + audit | Retry propose/approve deliberately | None |
| Adapter verify failure | Action status | Auto-rollback when reversible → `ROLLED_BACK`/`FAILED`; **never `VERIFIED`** | Inspect audit; re-propose if needed | None |
| Rollback failure | Action status | `ROLLBACK_FAILED` / `FAILED` | Operator intervention | None (simulated plane) |
| Process crash mid-`EXECUTING` | Startup recovery | Reclaim → `FAILED` + `recovered_stale_executing`; **no auto-replay** | Restart API | None for durable rows |
| Process crash mid-`APPROVED` (pre-exec) | Startup recovery | Reclaim → `FAILED` + `recovered_stale_approved` | Restart API | None |

## Startup recovery (implemented)

On API lifespan after `init_db()`:

1. Find durable `EXECUTING` → mark `FAILED`, audit `recovered_stale_executing`
2. Find `APPROVED` with no `executed_at` → mark `FAILED`, audit `recovered_stale_approved`
3. Sweep expired `ACTIVE` actions
4. Expose summary on `/api/ops/status` → `recovery`

**Invariant:** a failed or incomplete security action is never reported as `VERIFIED` / successful mitigation.

## Backup / restore procedure

```bash
# Backup (consistent SQLite snapshot)
python scripts/40_db_backup_restore.py backup --out backups/aegis.db

# Restore to a path (stop writers first in real ops)
python scripts/40_db_backup_restore.py restore --from backups/aegis.db --target database/ids_restored.db

# Verify tables + orphan audit check
python scripts/40_db_backup_restore.py verify --db database/ids_restored.db

# Full drill: backup → destroy copy → restore → verify
python scripts/40_db_backup_restore.py disaster-drill --work-dir backups/drill
```

Also recover (outside DB):

- Model artifacts under `models/trained_models/` (P0 freeze / `model_version_refs`)
- `config.yaml` + `.env`
- Alembic head (`alembic upgrade head`)

## Measured RPO / RTO (test environment)

From `disaster-drill` on the development host (SQLite file ~0.5 MB):

| Metric | Measured / configured | Notes |
|--------|----------------------|-------|
| **RTO** | **~0.02 s** wall time for backup→destroy→restore→verify in drill | Scripted local file restore only |
| **Drill RPO** | **≈ 0** relative to backup taken immediately before destruction | No writes between backup and destroy in drill |
| **Operational RPO** | Time since last successful operator backup | Schedule-dependent; not continuous replication |

**Limitations:** Not an enterprise DR guarantee. In-process queue jobs, metrics buffers, and TestNetworkAdapter memory state are **not** in the DB backup.

## Tests

`tests/test_productionization_p9_recovery.py` — readiness fail-closed, model miss, EXECUTING/APPROVED reclaim, verify/rollback failure, queue error, PCAP reject, backup/restore integrity.

## Related

- P6 persistence (what is durable)
- P7 readiness / ops status
- P8 queue saturation (no silent drop)
- P3 adapter verify/rollback lifecycle
