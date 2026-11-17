"""R1a: persist Zero-Day Gate alerts and record which detector raised each incident.

Revision ID: 003_zero_day_gate
Revises: 002_p6_persistence
Create Date: 2026-11-17
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "003_zero_day_gate"
down_revision: Union[str, None] = "002_p6_persistence"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if "incidents" in tables:
        cols = {c["name"] for c in inspector.get_columns("incidents")}
        with op.batch_alter_table("incidents") as batch:
            if "detector_source" not in cols:
                batch.add_column(sa.Column("detector_source", sa.String(length=16), nullable=True))
            if "zero_day_label" not in cols:
                batch.add_column(sa.Column("zero_day_label", sa.String(length=32), nullable=True))
            if "zero_day_p_value" not in cols:
                batch.add_column(sa.Column("zero_day_p_value", sa.Float(), nullable=True))

    if "zero_day_alerts" not in tables:
        op.create_table(
            "zero_day_alerts",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("origin", sa.String(length=16), nullable=True),
            sa.Column("source_ref", sa.String(length=128), nullable=True),
            sa.Column("incident_code", sa.String(length=32), nullable=True),
            sa.Column("policy", sa.String(length=16), nullable=True),
            sa.Column("raised_incident", sa.Integer(), nullable=True),
            sa.Column("gate_label", sa.String(length=32), nullable=True),
            sa.Column("p_value", sa.Float(), nullable=True),
            sa.Column("alpha", sa.Float(), nullable=True),
            sa.Column("fused_surprisal", sa.Float(), nullable=True),
            sa.Column("p_attack", sa.Float(), nullable=True),
            sa.Column("knn_distance", sa.Float(), nullable=True),
            sa.Column("family_predicted", sa.String(length=32), nullable=True),
            sa.Column("family_conformity_p", sa.Float(), nullable=True),
            sa.Column("frozen_is_attack", sa.Integer(), nullable=True),
            sa.Column("frozen_attack_type", sa.String(length=64), nullable=True),
            sa.Column("gate_model_version", sa.String(length=64), nullable=True),
            sa.Column("evidence", sa.Text(), nullable=True),
        )
        op.create_index("ix_zero_day_alerts_id", "zero_day_alerts", ["id"])
        op.create_index("ix_zero_day_alerts_created_at", "zero_day_alerts", ["created_at"])
        op.create_index("ix_zero_day_alerts_incident_code", "zero_day_alerts", ["incident_code"])


def downgrade() -> None:
    op.drop_index("ix_zero_day_alerts_incident_code", table_name="zero_day_alerts")
    op.drop_index("ix_zero_day_alerts_created_at", table_name="zero_day_alerts")
    op.drop_index("ix_zero_day_alerts_id", table_name="zero_day_alerts")
    op.drop_table("zero_day_alerts")
    with op.batch_alter_table("incidents") as batch:
        batch.drop_column("zero_day_p_value")
        batch.drop_column("zero_day_label")
        batch.drop_column("detector_source")
