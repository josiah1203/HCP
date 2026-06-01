"""Org invite tokens (Phase 0.5 signup/invite MVP)

Revision ID: 009
Revises: 008
Create Date: 2026-06-01

"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "009"
down_revision: Union[str, None] = "008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "org_invites",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "email",
            sa.Text(),
            nullable=False,
        ),
        sa.Column("role", sa.Text(), nullable=False, server_default="viewer"),
        sa.Column("token_hash", sa.Text(), nullable=False),
        sa.Column("invited_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("accepted_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["org_id"], ["orgs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["invited_by"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["accepted_user_id"], ["users.id"], ondelete="SET NULL"
        ),
        sa.UniqueConstraint("org_id", "email", name="org_invites_org_email_unique"),
        sa.UniqueConstraint("token_hash"),
    )
    op.create_index("ix_org_invites_token_hash", "org_invites", ["token_hash"])


def downgrade() -> None:
    op.drop_index("ix_org_invites_token_hash", table_name="org_invites")
    op.drop_table("org_invites")
