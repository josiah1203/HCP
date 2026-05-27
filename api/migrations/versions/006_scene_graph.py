"""Scene graph persistence tables

Revision ID: 006
Revises: 005
Create Date: 2026-05-26

"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "006"
down_revision: Union[str, None] = "005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "component_identities",
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
        sa.Column("canonical_key", sa.Text(), nullable=False),
        sa.Column("source_tool", sa.Text(), nullable=True),
        sa.Column("source_ref", sa.Text(), nullable=True),
        sa.Column("metadata", postgresql.JSONB(), nullable=True),
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
            "canonical_key",
            name="component_identities_unique",
        ),
    )
    op.create_index(
        "ix_component_identities_org_project",
        "component_identities",
        ["org_id", "project_id"],
    )

    op.create_table(
        "scene_graph_nodes",
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
        sa.Column("node_key", sa.Text(), nullable=False),
        sa.Column(
            "identity_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("component_identities.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("transform", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("metadata", postgresql.JSONB(), nullable=True),
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
        sa.UniqueConstraint("org_id", "project_id", "node_key", name="scene_graph_nodes_unique"),
    )
    op.create_index(
        "ix_scene_graph_nodes_org_project",
        "scene_graph_nodes",
        ["org_id", "project_id"],
    )

    op.create_table(
        "scene_graph_edges",
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
        sa.Column("edge_key", sa.Text(), nullable=False),
        sa.Column("from_node_key", sa.Text(), nullable=False),
        sa.Column("to_node_key", sa.Text(), nullable=False),
        sa.Column("constraint_type", sa.Text(), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=True),
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
        sa.UniqueConstraint("org_id", "project_id", "edge_key", name="scene_graph_edges_unique"),
    )
    op.create_index(
        "ix_scene_graph_edges_org_project",
        "scene_graph_edges",
        ["org_id", "project_id"],
    )
    op.create_index(
        "ix_scene_graph_edges_org_project_from",
        "scene_graph_edges",
        ["org_id", "project_id", "from_node_key"],
    )
    op.create_index(
        "ix_scene_graph_edges_org_project_to",
        "scene_graph_edges",
        ["org_id", "project_id", "to_node_key"],
    )

    op.create_table(
        "scene_graph_snapshots",
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
            "commit_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("hos_commits.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("snapshot", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column(
            "created_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.UniqueConstraint("org_id", "project_id", "commit_id", name="scene_graph_snapshots_unique"),
    )
    op.create_index(
        "ix_scene_graph_snapshots_org_project",
        "scene_graph_snapshots",
        ["org_id", "project_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_scene_graph_snapshots_org_project", table_name="scene_graph_snapshots")
    op.drop_table("scene_graph_snapshots")
    op.drop_index("ix_scene_graph_edges_org_project_to", table_name="scene_graph_edges")
    op.drop_index("ix_scene_graph_edges_org_project_from", table_name="scene_graph_edges")
    op.drop_index("ix_scene_graph_edges_org_project", table_name="scene_graph_edges")
    op.drop_table("scene_graph_edges")
    op.drop_index("ix_scene_graph_nodes_org_project", table_name="scene_graph_nodes")
    op.drop_table("scene_graph_nodes")
    op.drop_index("ix_component_identities_org_project", table_name="component_identities")
    op.drop_table("component_identities")

