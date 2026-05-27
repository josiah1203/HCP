"""HOS version control tables

Revision ID: 004
Revises: 003
Create Date: 2026-05-26

"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "hos_commits",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "org_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("orgs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "project_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "branch_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column(
            "created_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column("tree", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
    )

    op.create_table(
        "hos_branches",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "org_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("orgs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "project_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column(
            "head_commit_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column(
            "created_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.UniqueConstraint("org_id", "project_id", "name", name="hos_branches_unique"),
    )

    op.create_foreign_key(
        "hos_commits_branch_id_fkey",
        "hos_commits",
        "hos_branches",
        ["branch_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "hos_branches_head_commit_id_fkey",
        "hos_branches",
        "hos_commits",
        ["head_commit_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.create_table(
        "hos_commit_parents",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "org_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("orgs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "commit_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("hos_commits.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "parent_commit_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("hos_commits.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("parent_order", sa.SmallInteger(), nullable=False, server_default="0"),
        sa.UniqueConstraint(
            "commit_id", "parent_commit_id", name="hos_commit_parents_unique"
        ),
    )

    op.create_table(
        "hos_merges",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "org_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("orgs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "project_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "target_branch_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("hos_branches.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "source_branch_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("hos_branches.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "target_head_commit_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("hos_commits.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "source_head_commit_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("hos_commits.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("status", sa.Text(), nullable=False, server_default="conflicts"),
        sa.Column(
            "result_commit_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("hos_commits.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
    )

    op.create_table(
        "hos_conflicts",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "org_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("orgs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "project_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "merge_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("hos_merges.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("path", sa.Text(), nullable=False),
        sa.Column("base", postgresql.JSONB(), nullable=True),
        sa.Column("ours", postgresql.JSONB(), nullable=True),
        sa.Column("theirs", postgresql.JSONB(), nullable=True),
        sa.Column("resolution", postgresql.JSONB(), nullable=True),
        sa.Column("status", sa.Text(), nullable=False, server_default="unresolved"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "resolved_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=True,
        ),
        sa.UniqueConstraint("merge_id", "path", name="hos_conflicts_merge_path_unique"),
    )

    op.create_table(
        "hos_audit_log",
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
        sa.Column("entity_type", sa.Text(), nullable=False),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_type", sa.Text(), nullable=False),
        sa.Column(
            "actor_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column("actor_email", sa.Text(), nullable=False),
        sa.Column("metadata", postgresql.JSONB(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
    )

    op.create_index(
        "idx_hos_branches_org_project",
        "hos_branches",
        ["org_id", "project_id"],
    )
    op.create_index("idx_hos_commits_org_project", "hos_commits", ["org_id", "project_id"])
    op.create_index(
        "idx_hos_commits_project_created",
        "hos_commits",
        ["project_id", sa.text("created_at DESC")],
    )
    op.create_index("idx_hos_merges_org_project", "hos_merges", ["org_id", "project_id"])
    op.create_index(
        "idx_hos_conflicts_merge",
        "hos_conflicts",
        ["merge_id"],
        postgresql_where=sa.text("status = 'unresolved'"),
    )
    op.create_index(
        "idx_hos_audit_org_created",
        "hos_audit_log",
        ["org_id", sa.text("created_at DESC")],
    )


def downgrade() -> None:
    op.drop_constraint("hos_branches_head_commit_id_fkey", "hos_branches", type_="foreignkey")
    op.drop_constraint("hos_commits_branch_id_fkey", "hos_commits", type_="foreignkey")
    op.drop_index("idx_hos_audit_org_created", table_name="hos_audit_log")
    op.drop_index("idx_hos_conflicts_merge", table_name="hos_conflicts")
    op.drop_index("idx_hos_merges_org_project", table_name="hos_merges")
    op.drop_index("idx_hos_commits_project_created", table_name="hos_commits")
    op.drop_index("idx_hos_commits_org_project", table_name="hos_commits")
    op.drop_index("idx_hos_branches_org_project", table_name="hos_branches")
    op.drop_table("hos_audit_log")
    op.drop_table("hos_conflicts")
    op.drop_table("hos_merges")
    op.drop_table("hos_commit_parents")
    op.drop_table("hos_commits")
    op.drop_table("hos_branches")

