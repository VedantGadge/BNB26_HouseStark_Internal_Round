"""Add verified platform-specific export artifacts."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0006_platform_exports"
down_revision: str | None = "0005_edit_versions_renders"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "platform_exports",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("edit_version_id", sa.Uuid(), nullable=False),
        sa.Column("asset_id", sa.Uuid(), nullable=False),
        sa.Column("preset", sa.String(length=64), nullable=False),
        sa.Column("platform", sa.String(length=64), nullable=False),
        sa.Column("derived_recipe", sa.JSON(), nullable=False),
        sa.Column("supporting_copy", sa.Text(), nullable=True),
        sa.Column("hashtags", sa.JSON(), nullable=False),
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
    op.create_index("ix_platform_exports_asset_id", "platform_exports", ["asset_id"])
    op.create_index("ix_platform_exports_edit_version_id", "platform_exports", ["edit_version_id"])
    op.create_index("ix_platform_exports_platform", "platform_exports", ["platform"])
    op.create_index("ix_platform_exports_preset", "platform_exports", ["preset"])
    op.create_index(
        "ix_platform_exports_processing_status", "platform_exports", ["processing_status"]
    )


def downgrade() -> None:
    op.drop_index("ix_platform_exports_processing_status", table_name="platform_exports")
    op.drop_index("ix_platform_exports_preset", table_name="platform_exports")
    op.drop_index("ix_platform_exports_platform", table_name="platform_exports")
    op.drop_index("ix_platform_exports_edit_version_id", table_name="platform_exports")
    op.drop_index("ix_platform_exports_asset_id", table_name="platform_exports")
    op.drop_table("platform_exports")
