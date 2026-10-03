"""Add persisted transcript and visual observations.

Revision ID: 0002_add_asset_analysis_records
Revises: 0001_initial_projects_and_assets
Create Date: 2026-10-03
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002_add_asset_analysis_records"
down_revision: str | None = "0001_initial_projects_and_assets"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "transcript_segments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("asset_id", sa.Uuid(), nullable=False),
        sa.Column("source_start_ms", sa.BigInteger(), nullable=False),
        sa.Column("source_end_ms", sa.BigInteger(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("word_timings", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("source_end_ms > source_start_ms", name="ck_transcript_segments_positive_range"),
        sa.CheckConstraint("source_start_ms >= 0", name="ck_transcript_segments_start_nonnegative"),
        sa.ForeignKeyConstraint(["asset_id"], ["assets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_transcript_segments_asset_id", "transcript_segments", ["asset_id"])

    op.create_table(
        "visual_observations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("asset_id", sa.Uuid(), nullable=False),
        sa.Column("source_start_ms", sa.BigInteger(), nullable=False),
        sa.Column("source_end_ms", sa.BigInteger(), nullable=False),
        sa.Column("frame_references", sa.JSON(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("source_end_ms >= source_start_ms", name="ck_visual_observations_valid_range"),
        sa.CheckConstraint("source_start_ms >= 0", name="ck_visual_observations_start_nonnegative"),
        sa.ForeignKeyConstraint(["asset_id"], ["assets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_visual_observations_asset_id", "visual_observations", ["asset_id"])


def downgrade() -> None:
    op.drop_index("ix_visual_observations_asset_id", table_name="visual_observations")
    op.drop_table("visual_observations")
    op.drop_index("ix_transcript_segments_asset_id", table_name="transcript_segments")
    op.drop_table("transcript_segments")
