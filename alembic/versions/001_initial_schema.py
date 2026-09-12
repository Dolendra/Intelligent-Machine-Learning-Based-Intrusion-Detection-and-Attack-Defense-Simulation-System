"""Initial Aegis IDS schema (incidents, events, simulations).

Revision ID: 001_initial
Revises:
Create Date: 2026-09-12
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if "incidents" not in tables:
        op.create_table(
            "incidents",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("incident_code", sa.String(length=32), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("attack_type", sa.String(length=64), nullable=True),
            sa.Column("is_attack", sa.Integer(), nullable=True),
            sa.Column("confidence", sa.Float(), nullable=True),
            sa.Column("risk_score", sa.Float(), nullable=True),
            sa.Column("severity", sa.String(length=16), nullable=True),
            sa.Column("recommendation", sa.Text(), nullable=True),
            sa.Column("explanation", sa.Text(), nullable=True),
            sa.Column("status", sa.String(length=32), nullable=True),
            sa.Column("source_ref", sa.String(length=128), nullable=True),
            sa.Column("analyst_notes", sa.Text(), nullable=True),
            sa.Column("defense_action", sa.String(length=128), nullable=True),
            sa.Column("resolved_at", sa.DateTime(), nullable=True),
            sa.Column("asset_criticality", sa.Float(), nullable=True),
            sa.Column("campaign_id", sa.String(length=32), nullable=True),
            sa.Column("hit_count", sa.Integer(), nullable=True),
        )
        op.create_index("ix_incidents_id", "incidents", ["id"])
        op.create_index("ix_incidents_incident_code", "incidents", ["incident_code"], unique=True)
        op.create_index("ix_incidents_attack_type", "incidents", ["attack_type"])
        op.create_index("ix_incidents_severity", "incidents", ["severity"])
        op.create_index("ix_incidents_campaign_id", "incidents", ["campaign_id"])
    else:
        # Ensure newer columns exist on DBs created before Alembic
        cols = {c["name"] for c in inspector.get_columns("incidents")}
        with op.batch_alter_table("incidents") as batch:
            if "analyst_notes" not in cols:
                batch.add_column(sa.Column("analyst_notes", sa.Text(), nullable=True))
            if "defense_action" not in cols:
                batch.add_column(sa.Column("defense_action", sa.String(length=128), nullable=True))
            if "resolved_at" not in cols:
                batch.add_column(sa.Column("resolved_at", sa.DateTime(), nullable=True))
            if "asset_criticality" not in cols:
                batch.add_column(sa.Column("asset_criticality", sa.Float(), nullable=True))
            if "campaign_id" not in cols:
                batch.add_column(sa.Column("campaign_id", sa.String(length=32), nullable=True))
            if "hit_count" not in cols:
                batch.add_column(sa.Column("hit_count", sa.Integer(), nullable=True))

    if "simulations" not in tables:
        op.create_table(
            "simulations",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("session_id", sa.String(length=64), nullable=True),
            sa.Column("attack_type", sa.String(length=64), nullable=True),
            sa.Column("state", sa.String(length=32), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("payload", sa.Text(), nullable=True),
        )
        op.create_index("ix_simulations_id", "simulations", ["id"])
        op.create_index("ix_simulations_session_id", "simulations", ["session_id"], unique=True)

    if "incident_events" not in tables:
        op.create_table(
            "incident_events",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("incident_code", sa.String(length=32), nullable=True),
            sa.Column("timestamp", sa.DateTime(), nullable=True),
            sa.Column("old_status", sa.String(length=32), nullable=True),
            sa.Column("new_status", sa.String(length=32), nullable=True),
            sa.Column("actor", sa.String(length=64), nullable=True),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("action", sa.String(length=64), nullable=True),
        )
        op.create_index("ix_incident_events_id", "incident_events", ["id"])
        op.create_index("ix_incident_events_incident_code", "incident_events", ["incident_code"])


def downgrade() -> None:
    op.drop_table("incident_events")
    op.drop_table("simulations")
    op.drop_table("incidents")
