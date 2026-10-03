"""Create the project and asset foundations.

Revision ID: 0001_initial_projects_and_assets
Revises:
Create Date: 2026-10-03
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001_initial_projects_and_assets"
down_revision: str | None = None
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "projects",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("owner_id", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("brief", sa.Text(), nullable=False),
        sa.Column("audience", sa.String(length=500), nullable=True),
        sa.Column("tone", sa.String(length=120), nullable=True),
        sa.Column("target_platforms", sa.JSON(), nullable=False),
        sa.Column("workflow_stage", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_projects_owner_id", "projects", ["owner_id"], unique=False)
    op.create_index("ix_projects_workflow_stage", "projects", ["workflow_stage"], unique=False)

    op.create_table(
        "assets",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("owner_id", sa.String(length=255), nullable=False),
        sa.Column("kind", sa.String(length=16), nullable=False),
        sa.Column("provider_asset_id", sa.String(length=255), nullable=True),
        sa.Column("public_id", sa.String(length=500), nullable=False),
        sa.Column("resource_type", sa.String(length=16), nullable=False),
        sa.Column("delivery_type", sa.String(length=32), nullable=False),
        sa.Column("provider_version", sa.String(length=64), nullable=True),
        sa.Column("format", sa.String(length=32), nullable=True),
        sa.Column("byte_size", sa.BigInteger(), nullable=True),
        sa.Column("width", sa.Integer(), nullable=True),
        sa.Column("height", sa.Integer(), nullable=True),
        sa.Column("duration_ms", sa.BigInteger(), nullable=True),
        sa.Column("tags", sa.JSON(), nullable=False),
        sa.Column("processing_status", sa.String(length=32), nullable=False),
        sa.Column("processing_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("provider_asset_id"),
        sa.UniqueConstraint("public_id"),
    )
    op.create_index("ix_assets_owner_id", "assets", ["owner_id"], unique=False)
    op.create_index("ix_assets_project_id", "assets", ["project_id"], unique=False)
    op.create_index("ix_assets_processing_status", "assets", ["processing_status"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_assets_processing_status", table_name="assets")
    op.drop_index("ix_assets_project_id", table_name="assets")
    op.drop_index("ix_assets_owner_id", table_name="assets")
    op.drop_table("assets")
    op.drop_index("ix_projects_workflow_stage", table_name="projects")
    op.drop_index("ix_projects_owner_id", table_name="projects")
    op.drop_table("projects")
