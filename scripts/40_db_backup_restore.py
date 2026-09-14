#!/usr/bin/env python
"""P9 database backup / restore with integrity verification (SQLite-first).

Usage:
  python scripts/40_db_backup_restore.py backup --out backups/aegis.db
  python scripts/40_db_backup_restore.py restore --from backups/aegis.db --target database/ids_restored.db
  python scripts/40_db_backup_restore.py verify --db database/ids_restored.db
  python scripts/40_db_backup_restore.py disaster-drill   # backup → destroy copy → restore → verify

Does not claim enterprise DR. Measures RPO/RTO for the tested procedure.
"""
from __future__ import annotations

import argparse
import json
import shutil
import sqlite3
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ids_config import ROOT as PROJECT_ROOT


REQUIRED_TABLES = (
    "users",
    "incidents",
    "incident_events",
    "response_actions",
    "response_audit_events",
    "security_audit_events",
    "simulations",
    "model_version_refs",
)


def _default_db_path() -> Path:
    import os

    env = os.getenv("IDS_DB_PATH")
    if env:
        return Path(env)
    return PROJECT_ROOT / "database" / "ids.db"


def backup_sqlite(src: Path, dest: Path) -> dict:
    dest.parent.mkdir(parents=True, exist_ok=True)
    t0 = time.perf_counter()
    # Consistent snapshot via SQLite backup API
    src_conn = sqlite3.connect(str(src))
    try:
        dest_conn = sqlite3.connect(str(dest))
        try:
            src_conn.backup(dest_conn)
        finally:
            dest_conn.close()
    finally:
        src_conn.close()
    elapsed = time.perf_counter() - t0
    return {
        "ok": True,
        "src": str(src),
        "dest": str(dest),
        "bytes": dest.stat().st_size,
        "elapsed_s": round(elapsed, 4),
        "method": "sqlite3.Connection.backup",
    }


def restore_sqlite(backup_path: Path, target: Path) -> dict:
    target.parent.mkdir(parents=True, exist_ok=True)
    t0 = time.perf_counter()
    if target.exists():
        target.unlink()
    shutil.copy2(backup_path, target)
    elapsed = time.perf_counter() - t0
    return {
        "ok": True,
        "from": str(backup_path),
        "target": str(target),
        "bytes": target.stat().st_size,
        "elapsed_s": round(elapsed, 4),
        "method": "file_copy_from_backup",
    }


def verify_db(db_path: Path) -> dict:
    t0 = time.perf_counter()
    conn = sqlite3.connect(str(db_path))
    try:
        tables = {
            r[0]
            for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        missing = [t for t in REQUIRED_TABLES if t not in tables]
        counts = {}
        for t in REQUIRED_TABLES:
            if t in tables:
                counts[t] = conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        # Relationship spot-check: response audit FKs exist as action_ids
        orphan_audits = 0
        if "response_actions" in tables and "response_audit_events" in tables:
            orphan_audits = conn.execute(
                """
                SELECT COUNT(*) FROM response_audit_events a
                WHERE NOT EXISTS (
                  SELECT 1 FROM response_actions r WHERE r.action_id = a.action_id
                )
                """
            ).fetchone()[0]
    finally:
        conn.close()
    elapsed = time.perf_counter() - t0
    return {
        "ok": not missing and orphan_audits == 0,
        "db": str(db_path),
        "missing_tables": missing,
        "counts": counts,
        "orphan_response_audits": orphan_audits,
        "elapsed_s": round(elapsed, 4),
    }


def disaster_drill(src: Path, work_dir: Path) -> dict:
    """Backup → destroy working copy → restore → verify. Measures RTO."""
    work_dir.mkdir(parents=True, exist_ok=True)
    backup_path = work_dir / f"drill_backup_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.db"
    destroyed = work_dir / "destroyed.db"
    restored = work_dir / "restored.db"

    wall0 = time.perf_counter()
    # Seed working copy from source
    shutil.copy2(src, destroyed)
    pre = verify_db(destroyed)
    b = backup_sqlite(destroyed, backup_path)
    # Destroy
    destroyed.unlink()
    destroyed_exists = destroyed.exists()
    r = restore_sqlite(backup_path, restored)
    v = verify_db(restored)
    wall = time.perf_counter() - wall0

    # RPO for this drill: last backup is the destruction point → theoretical loss = 0
    # relative to post-backup writes (none in this drill).
    return {
        "ok": v.get("ok") and not destroyed_exists and b.get("ok") and r.get("ok"),
        "pre_verify": pre,
        "backup": b,
        "destroyed_exists": destroyed_exists,
        "restore": r,
        "post_verify": v,
        "rto_seconds_measured": round(wall, 4),
        "rpo_notes": [
            "Drill RPO ≈ 0 relative to the backup taken immediately before destruction.",
            "Operational RPO equals time since last successful backup under the operator schedule.",
        ],
        "phase": "P9",
        "not_enterprise_dr": True,
    }


def main() -> int:
    p = argparse.ArgumentParser(description="P9 SQLite backup/restore drill")
    sub = p.add_subparsers(dest="cmd", required=True)

    b = sub.add_parser("backup")
    b.add_argument("--src", type=Path, default=None)
    b.add_argument("--out", type=Path, required=True)

    r = sub.add_parser("restore")
    r.add_argument("--from", dest="backup", type=Path, required=True)
    r.add_argument("--target", type=Path, required=True)

    v = sub.add_parser("verify")
    v.add_argument("--db", type=Path, required=True)

    d = sub.add_parser("disaster-drill")
    d.add_argument("--src", type=Path, default=None)
    d.add_argument("--work-dir", type=Path, default=PROJECT_ROOT / "backups" / "drill")

    args = p.parse_args()
    src = args.src if getattr(args, "src", None) else _default_db_path()

    if args.cmd == "backup":
        if not src.exists():
            # Ensure schema exists for empty environments
            from database.db import init_db

            init_db()
        out = backup_sqlite(src, args.out)
    elif args.cmd == "restore":
        out = restore_sqlite(args.backup, args.target)
    elif args.cmd == "verify":
        out = verify_db(args.db)
    else:
        if not src.exists():
            from database.db import init_db

            init_db()
        out = disaster_drill(src, args.work_dir)

    print(json.dumps(out, indent=2))
    return 0 if out.get("ok", True) else 1


if __name__ == "__main__":
    raise SystemExit(main())
