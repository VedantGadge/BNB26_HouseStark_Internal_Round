"""Add immutable edit recipes and their derived MP4 render records."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005_edit_versions_renders"
down_revision: str | None = "0004_add_clip_candidates"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "edit_versions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("candidate_id", sa.Uuid(), nullable=False),
        sa.Column("asset_id", sa.Uuid(), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("parent_version_id", sa.Uuid(), nullable=True),
        sa.Column("author_type", sa.String(length=32), nullable=False),
        sa.Column("recipe", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["asset_id"], ["assets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["candidate_id"], ["clip_candidates.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["parent_version_id"], ["edit_versions.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("candidate_id", "revision", name="uq_edit_versions_candidate_revision"),
    )
    op.create_index("ix_edit_versions_asset_id", "edit_versions", ["asset_id"])
    op.create_index("ix_edit_versions_candidate_id", "edit_versions", ["candidate_id"])
    op.create_table(
        "edit_renders",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("edit_version_id", sa.Uuid(), nullable=False),
        sa.Column("asset_id", sa.Uuid(), nullable=False),
        sa.Column("public_id", sa.String(length=500), nullable=False),
        sa.Column("provider_asset_id", sa.String(length=255), nullable=True),
        sa.Column("provider_version", sa.String(length=64), nullable=True),
        sa.Column("format", sa.String(length=32), nullable=False),
        sa.Column("width", sa.Integer(), nullable=True),
        sa.Column("height", sa.Integer(), nullable=True),
        sa.Column("duration_ms", sa.BigInteger(), nullable=True),
        sa.Column("processing_status", sa.String(length=32), nullable=False),
        sa.Column("processing_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["asset_id"], ["assets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["edit_version_id"], ["edit_versions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("public_id"),
    )
    op.create_index("ix_edit_renders_asset_id", "edit_renders", ["asset_id"])
    op.create_index("ix_edit_renders_edit_version_id", "edit_renders", ["edit_version_id"])
    op.create_index("ix_edit_renders_processing_status", "edit_renders", ["processing_status"])


def downgrade() -> None:
    op.drop_index("ix_edit_renders_processing_status", table_name="edit_renders")
    op.drop_index("ix_edit_renders_edit_version_id", table_name="edit_renders")
    op.drop_index("ix_edit_renders_asset_id", table_name="edit_renders")
    op.drop_table("edit_renders")
    op.drop_index("ix_edit_versions_candidate_id", table_name="edit_versions")
    op.drop_index("ix_edit_versions_asset_id", table_name="edit_versions")
    op.drop_table("edit_versions")
