"""Add source-grounded script alignment records."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003_add_script_alignments"
down_revision: str | None = "0002_add_asset_analysis_records"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "script_alignments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("asset_id", sa.Uuid(), nullable=False),
        sa.Column("source_start_ms", sa.BigInteger(), nullable=False),
        sa.Column("source_end_ms", sa.BigInteger(), nullable=False),
        sa.Column("script_beat", sa.Text(), nullable=False),
        sa.Column("evidence_text", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["asset_id"], ["assets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_script_alignments_asset_id", "script_alignments", ["asset_id"])


def downgrade() -> None:
    op.drop_index("ix_script_alignments_asset_id", table_name="script_alignments")
    op.drop_table("script_alignments")
