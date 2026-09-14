"""P6 bootstrap: seed users + frozen model artifact references after migrations."""
from __future__ import annotations

import logging
from pathlib import Path

from database.db import ModelVersionRef, SessionLocal
from ids_config import ROOT

logger = logging.getLogger("aegis.db")

# Frozen research baseline references (paths only — never rewrite trained weights).
_MODEL_REFS = (
    ("binary_decision_tree", "models/trained_models/binary_decision_tree.joblib", "v1.1-research"),
    ("multiclass_random_forest", "models/trained_models/multiclass_random_forest.joblib", "v1.1-research"),
    ("feature_columns", "models/trained_models/feature_columns.json", "v1.1-research"),
)


def seed_model_version_refs() -> int:
    created = 0
    with SessionLocal() as db:
        for name, rel, tag in _MODEL_REFS:
            existing = db.query(ModelVersionRef).filter(ModelVersionRef.name == name).first()
            path = str((ROOT / rel).as_posix())
            notes = "Immutable research baseline artifact reference (P0 freeze)."
            if existing is None:
                db.add(
                    ModelVersionRef(
                        name=name,
                        path=path,
                        version_tag=tag,
                        notes=notes,
                    )
                )
                created += 1
            else:
                existing.path = path
                existing.version_tag = tag
                existing.notes = notes
        db.commit()
    return created


def bootstrap_persistence() -> None:
    """Call after init_db() so durable directories exist."""
    try:
        from security.auth.users import user_store

        user_store.ensure_seeded()
    except Exception as exc:  # noqa: BLE001
        logger.warning("User seed skipped: %s", exc)
    try:
        seed_model_version_refs()
    except Exception as exc:  # noqa: BLE001
        logger.warning("Model ref seed skipped: %s", exc)
