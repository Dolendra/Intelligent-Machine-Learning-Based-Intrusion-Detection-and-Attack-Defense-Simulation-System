"""P6 persistence: users, response actions, audit events, model refs.

Revision ID: 002_p6_persistence
Revises: 001_initial
Create Date: 2026-09-15
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "002_p6_persistence"
down_revision: Union[str, None] = "001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if "users" not in tables:
        op.create_table(
            "users",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("user_id", sa.String(length=64), nullable=False),
            sa.Column("username", sa.String(length=64), nullable=False),
            sa.Column("role", sa.String(length=32), nullable=False),
            sa.Column("password_hash", sa.String(length=256), nullable=False),
            sa.Column("active", sa.Integer(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
        )
        op.create_index("ix_users_id", "users", ["id"])
        op.create_index("ix_users_user_id", "users", ["user_id"], unique=True)
        op.create_index("ix_users_username", "users", ["username"], unique=True)

    if "response_actions" not in tables:
        op.create_table(
            "response_actions",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("action_id", sa.String(length=64), nullable=False),
            sa.Column("action_type", sa.String(length=32), nullable=False),
            sa.Column("incident_id", sa.String(length=64), nullable=True),
            sa.Column("source", sa.String(length=64), nullable=True),
            sa.Column("target", sa.String(length=256), nullable=False),
            sa.Column("reason", sa.Text(), nullable=True),
            sa.Column("risk_score", sa.Float(), nullable=True),
            sa.Column("severity", sa.String(length=16), nullable=True),
            sa.Column("duration_minutes", sa.Integer(), nullable=True),
            sa.Column("mode", sa.String(length=32), nullable=True),
            sa.Column("adapter", sa.String(length=64), nullable=True),
            sa.Column("status", sa.String(length=32), nullable=True),
            sa.Column("created_at", sa.String(length=64), nullable=True),
            sa.Column("created_by", sa.String(length=64), nullable=True),
            sa.Column("approved_at", sa.String(length=64), nullable=True),
            sa.Column("approved_by", sa.String(length=64), nullable=True),
            sa.Column("rejected_at", sa.String(length=64), nullable=True),
            sa.Column("rejected_by", sa.String(length=64), nullable=True),
            sa.Column("rejection_reason", sa.Text(), nullable=True),
            sa.Column("executed_at", sa.String(length=64), nullable=True),
            sa.Column("verified_at", sa.String(length=64), nullable=True),
            sa.Column("expires_at", sa.String(length=64), nullable=True),
            sa.Column("rolled_back_at", sa.String(length=64), nullable=True),
            sa.Column("result", sa.Text(), nullable=True),
            sa.Column("dry_run_preview", sa.Text(), nullable=True),
            sa.Column("rollback_status", sa.String(length=64), nullable=True),
            sa.Column("reversible", sa.Integer(), nullable=True),
            sa.Column("inverse_action", sa.String(length=32), nullable=True),
            sa.Column("attack_type", sa.String(length=64), nullable=True),
            sa.Column("live_network_change", sa.Integer(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
        )
        op.create_index("ix_response_actions_id", "response_actions", ["id"])
        op.create_index("ix_response_actions_action_id", "response_actions", ["action_id"], unique=True)
        op.create_index("ix_response_actions_incident_id", "response_actions", ["incident_id"])
        op.create_index("ix_response_actions_status", "response_actions", ["status"])

    if "response_audit_events" not in tables:
        op.create_table(
            "response_audit_events",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("action_id", sa.String(length=64), nullable=False),
            sa.Column("event", sa.String(length=64), nullable=False),
            sa.Column("timestamp", sa.String(length=64), nullable=False),
            sa.Column("actor", sa.String(length=64), nullable=True),
            sa.Column("detail_json", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
        )
        op.create_index("ix_response_audit_events_id", "response_audit_events", ["id"])
        op.create_index("ix_response_audit_events_action_id", "response_audit_events", ["action_id"])
        op.create_index("ix_response_audit_events_event", "response_audit_events", ["event"])

    if "security_audit_events" not in tables:
        op.create_table(
            "security_audit_events",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("event", sa.String(length=64), nullable=False),
            sa.Column("timestamp", sa.String(length=64), nullable=False),
            sa.Column("request_id", sa.String(length=64), nullable=True),
            sa.Column("path", sa.String(length=256), nullable=True),
            sa.Column("method", sa.String(length=16), nullable=True),
            sa.Column("code", sa.String(length=64), nullable=True),
            sa.Column("user", sa.String(length=64), nullable=True),
            sa.Column("role", sa.String(length=32), nullable=True),
            sa.Column("client", sa.String(length=64), nullable=True),
            sa.Column("phase", sa.String(length=16), nullable=True),
            sa.Column("detail_json", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
        )
        op.create_index("ix_security_audit_events_id", "security_audit_events", ["id"])
        op.create_index("ix_security_audit_events_event", "security_audit_events", ["event"])
        op.create_index("ix_security_audit_events_request_id", "security_audit_events", ["request_id"])

    if "model_version_refs" not in tables:
        op.create_table(
            "model_version_refs",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("name", sa.String(length=128), nullable=False),
            sa.Column("path", sa.String(length=512), nullable=False),
            sa.Column("version_tag", sa.String(length=64), nullable=True),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
        )
        op.create_index("ix_model_version_refs_id", "model_version_refs", ["id"])
        op.create_index("ix_model_version_refs_name", "model_version_refs", ["name"], unique=True)


def downgrade() -> None:
    op.drop_table("model_version_refs")
    op.drop_table("security_audit_events")
    op.drop_table("response_audit_events")
    op.drop_table("response_actions")
    op.drop_table("users")
