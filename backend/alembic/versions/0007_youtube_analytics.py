"""Connect creator YouTube accounts and distinguish analytics reporting windows."""

import sqlalchemy as sa

from alembic import op

revision = "0007_youtube_analytics"
down_revision = "0006_media_workflow"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "youtube_connections",
        sa.Column("owner_id", sa.String(255), primary_key=True),
        sa.Column("channel_id", sa.String(128), nullable=False),
        sa.Column("channel_title", sa.String(255), nullable=False),
        sa.Column("encrypted_refresh_token", sa.Text(), nullable=False),
        sa.Column("connected_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "youtube_oauth_attempts",
        sa.Column("state_hash", sa.String(64), primary_key=True),
        sa.Column("owner_id", sa.String(255), nullable=False),
        sa.Column("project_id", sa.Uuid(), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_youtube_oauth_attempts_owner_id", "youtube_oauth_attempts", ["owner_id"])
    op.add_column(
        "performance_snapshots",
        sa.Column("reporting_basis", sa.String(32), nullable=False, server_default="manual"),
    )


def downgrade():
    op.drop_column("performance_snapshots", "reporting_basis")
    op.drop_table("youtube_oauth_attempts")
    op.drop_table("youtube_connections")
