"""HNF documents, commit object snapshots, scene snapshot format

Revision ID: 007
Revises: 006
Create Date: 2026-05-31

"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "007"
down_revision: Union[str, None] = "006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "hos_commits",
        sa.Column("tree_root_ref", sa.Text(), nullable=True),
    )

    op.create_table(
        "hnf_documents",
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
        sa.Column("document_uri", sa.Text(), nullable=False),
        sa.Column("content_hash", sa.Text(), nullable=True),
        sa.Column("body", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("validation_warnings", postgresql.JSONB(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "org_id",
            "project_id",
            "document_uri",
            name="hnf_documents_uri_unique",
        ),
    )
    op.create_index(
        "ix_hnf_documents_org_project",
        "hnf_documents",
        ["org_id", "project_id"],
    )

    op.create_table(
        "hos_object_snapshots",
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
            "commit_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("hos_commits.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("object_path", sa.Text(), nullable=False),
        sa.Column(
            "object_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("objects.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "version_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("versions.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("content_hash", sa.Text(), nullable=True),
        sa.Column("hnf_type", sa.Text(), nullable=False),
        sa.Column("domain", sa.Text(), nullable=True),
        sa.Column("refs", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column(
            "properties",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("snapshot_version", sa.SmallInteger(), nullable=False, server_default="1"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "commit_id",
            "object_path",
            name="hos_object_snapshots_commit_path_unique",
        ),
    )
    op.create_index(
        "ix_hos_object_snapshots_commit",
        "hos_object_snapshots",
        ["commit_id"],
    )
    op.create_index(
        "ix_hos_object_snapshots_org_project",
        "hos_object_snapshots",
        ["org_id", "project_id"],
    )

    op.add_column(
        "scene_graph_snapshots",
        sa.Column(
            "snapshot_format",
            sa.Text(),
            nullable=False,
            server_default="json",
        ),
    )


def downgrade() -> None:
    op.drop_column("scene_graph_snapshots", "snapshot_format")
    op.drop_index("ix_hos_object_snapshots_org_project", table_name="hos_object_snapshots")
    op.drop_index("ix_hos_object_snapshots_commit", table_name="hos_object_snapshots")
    op.drop_table("hos_object_snapshots")
    op.drop_index("ix_hnf_documents_org_project", table_name="hnf_documents")
    op.drop_table("hnf_documents")
    op.drop_column("hos_commits", "tree_root_ref")
