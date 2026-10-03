"""Add manual content workflow and publication persistence."""

import sqlalchemy as sa

from alembic import op

revision = "0002_content_workflow"
down_revision = "0001_script_feature_persistence"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "projects",
        sa.Column("workflow_revision", sa.Integer(), nullable=False, server_default="1"),
    )
    op.add_column(
        "projects",
        sa.Column("workflow_data", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
    )
    op.create_table(
        "content_publications",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("project_id", sa.Uuid(), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("platform", sa.String(32), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("planned_at", sa.DateTime(timezone=True)),
        sa.Column("published_at", sa.DateTime(timezone=True)),
        sa.Column("external_url", sa.String(2048)),
        sa.Column("package_snapshot", sa.JSON(), nullable=False),
        sa.Column("supporting_copy", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.UniqueConstraint("project_id", "platform", name="uq_publication_platform"),
    )
    op.create_index("ix_content_publications_project_id", "content_publications", ["project_id"])


def downgrade() -> None:
    op.drop_table("content_publications")
    op.drop_column("projects", "workflow_data")
    op.drop_column("projects", "workflow_revision")
