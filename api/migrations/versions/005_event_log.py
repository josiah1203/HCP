"""Event stream append-only log

Revision ID: 005
Revises: 004
Create Date: 2026-05-26

"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "event_log",
        sa.Column("seq", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "event_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "project_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("event_type", sa.Text(), nullable=False),
        sa.Column("dedupe_key", sa.Text(), nullable=False),
        sa.Column(
            "actor_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=True,
        ),
        sa.Column("source", sa.Text(), nullable=False, server_default="api"),
        sa.Column("metadata", postgresql.JSONB(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.UniqueConstraint("event_id", name="event_log_event_id_unique"),
        sa.UniqueConstraint(
            "org_id",
            "project_id",
            "event_type",
            "dedupe_key",
            name="event_log_dedupe_unique",
        ),
    )
    op.create_index(
        "ix_event_log_org_project_seq",
        "event_log",
        ["org_id", "project_id", "seq"],
    )


def downgrade() -> None:
    op.drop_index("ix_event_log_org_project_seq", table_name="event_log")
    op.drop_table("event_log")

