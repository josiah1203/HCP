"""Artifact taxonomy metadata on objects and versions.

Revision ID: 003
Revises: 002
Create Date: 2026-05-25
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_DOMAIN_CHECK = (
    "domain IN ('electrical', 'mechanical', 'manufacturing', 'firmware', 'document')"
)
_REPRESENTATION_CHECK = "representation IN ('native', 'interchange', 'derived')"


def upgrade() -> None:
    op.add_column("objects", sa.Column("domain", sa.Text(), nullable=True))
    op.add_column("objects", sa.Column("source_tool", sa.Text(), nullable=True))
    op.add_column("objects", sa.Column("representation", sa.Text(), nullable=True))
    op.create_check_constraint("objects_domain_check", "objects", _DOMAIN_CHECK)
    op.create_check_constraint(
        "objects_representation_check", "objects", _REPRESENTATION_CHECK
    )

    op.add_column("versions", sa.Column("source_tool", sa.Text(), nullable=True))
    op.add_column(
        "versions", sa.Column("source_tool_version", sa.Text(), nullable=True)
    )
    op.add_column("versions", sa.Column("domain", sa.Text(), nullable=True))
    op.add_column("versions", sa.Column("representation", sa.Text(), nullable=True))
    op.add_column(
        "versions",
        sa.Column(
            "derived_from_version_id", postgresql.UUID(as_uuid=True), nullable=True
        ),
    )
    op.create_foreign_key(
        "versions_derived_from_version_id_fkey",
        "versions",
        "versions",
        ["derived_from_version_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_check_constraint("versions_domain_check", "versions", _DOMAIN_CHECK)
    op.create_check_constraint(
        "versions_representation_check", "versions", _REPRESENTATION_CHECK
    )

    op.create_index("idx_versions_domain", "versions", ["org_id", "domain"])
    op.create_index("idx_objects_domain", "objects", ["org_id", "domain"])


def downgrade() -> None:
    op.drop_index("idx_objects_domain", table_name="objects")
    op.drop_index("idx_versions_domain", table_name="versions")
    op.drop_constraint("versions_representation_check", "versions", type_="check")
    op.drop_constraint("versions_domain_check", "versions", type_="check")
    op.drop_constraint(
        "versions_derived_from_version_id_fkey", "versions", type_="foreignkey"
    )
    op.drop_column("versions", "derived_from_version_id")
    op.drop_column("versions", "representation")
    op.drop_column("versions", "domain")
    op.drop_column("versions", "source_tool_version")
    op.drop_column("versions", "source_tool")
    op.drop_constraint("objects_representation_check", "objects", type_="check")
    op.drop_constraint("objects_domain_check", "objects", type_="check")
    op.drop_column("objects", "representation")
    op.drop_column("objects", "source_tool")
    op.drop_column("objects", "domain")
