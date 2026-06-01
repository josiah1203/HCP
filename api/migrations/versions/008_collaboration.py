"""Collaboration presence and advisory soft locks (Phase 0.5 beta)

Revision ID: 008
Revises: 007
Create Date: 2026-05-31

"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "008"
down_revision: Union[str, None] = "007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "collaboration_presence",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "project_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("session_id", sa.Text(), nullable=False),
        sa.Column("resource_path", sa.Text(), nullable=True),
        sa.Column("domain", sa.Text(), nullable=True),
        sa.Column("client_meta", postgresql.JSONB(), nullable=True),
        sa.Column("last_heartbeat_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "org_id",
            "project_id",
            "user_id",
            "session_id",
            name="collaboration_presence_session_unique",
        ),
    )
    op.create_index(
        "ix_collaboration_presence_org_project",
        "collaboration_presence",
        ["org_id", "project_id"],
    )
    op.create_index(
        "ix_collaboration_presence_last_heartbeat",
        "collaboration_presence",
        ["org_id", "project_id", "last_heartbeat_at"],
    )

    op.create_table(
        "collaboration_soft_locks",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "project_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("resource_path", sa.Text(), nullable=False),
        sa.Column(
            "holder_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("holder_session_id", sa.Text(), nullable=True),
        sa.Column("advisory", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "org_id",
            "project_id",
            "resource_path",
            name="collaboration_soft_lock_resource_unique",
        ),
    )
    op.create_index(
        "ix_collaboration_soft_locks_org_project",
        "collaboration_soft_locks",
        ["org_id", "project_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_collaboration_soft_locks_org_project", table_name="collaboration_soft_locks")
    op.drop_table("collaboration_soft_locks")
    op.drop_index(
        "ix_collaboration_presence_last_heartbeat", table_name="collaboration_presence"
    )
    op.drop_index(
        "ix_collaboration_presence_org_project", table_name="collaboration_presence"
    )
    op.drop_table("collaboration_presence")
