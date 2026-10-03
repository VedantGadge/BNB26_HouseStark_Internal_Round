"""Add ranked automated clip candidates."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004_add_clip_candidates"
down_revision: str | None = "0003_add_script_alignments"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "clip_candidates",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("asset_id", sa.Uuid(), nullable=False),
        sa.Column("source_start_ms", sa.BigInteger(), nullable=False),
        sa.Column("source_end_ms", sa.BigInteger(), nullable=False),
        sa.Column("hook", sa.Text(), nullable=False),
        sa.Column("transcript_text", sa.Text(), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("reasons", sa.JSON(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["asset_id"], ["assets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_clip_candidates_asset_id", "clip_candidates", ["asset_id"])


def downgrade() -> None:
    op.drop_index("ix_clip_candidates_asset_id", table_name="clip_candidates")
    op.drop_table("clip_candidates")
