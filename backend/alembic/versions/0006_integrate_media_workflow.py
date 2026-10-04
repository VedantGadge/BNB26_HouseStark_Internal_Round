"""Connect immutable exports, source alignment, and sourced performance metrics."""

import sqlalchemy as sa

from alembic import op

revision = "0006_media_workflow"
down_revision = "0006_platform_exports"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("platform_exports", sa.Column("render_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        "fk_platform_render", "platform_exports", "edit_renders", ["render_id"], ["id"]
    )
    op.create_unique_constraint("uq_platform_render", "platform_exports", ["render_id"])
    op.add_column("clip_candidates", sa.Column("script_version_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        "fk_candidate_script",
        "clip_candidates",
        "ai_script_versions",
        ["script_version_id"],
        ["id"],
    )
    op.add_column("edit_renders", sa.Column("job_id", sa.Uuid(), nullable=True))
    op.create_foreign_key("fk_render_job", "edit_renders", "ai_script_jobs", ["job_id"], ["id"])
    op.create_unique_constraint("uq_render_job", "edit_renders", ["job_id"])
    op.add_column(
        "edit_renders",
        sa.Column("preset_name", sa.String(32), nullable=False, server_default="vertical"),
    )
    op.add_column("edit_renders", sa.Column("platform", sa.String(32), nullable=True))
    op.add_column(
        "edit_renders",
        sa.Column("supporting_copy", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
    )
    op.add_column(
        "edit_renders",
        sa.Column("recipe_snapshot", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
    )
    op.add_column("script_alignments", sa.Column("script_version_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        "fk_alignment_script",
        "script_alignments",
        "ai_script_versions",
        ["script_version_id"],
        ["id"],
    )
    op.add_column("script_alignments", sa.Column("section_id", sa.String(120), nullable=True))
    op.add_column(
        "script_alignments",
        sa.Column("match_status", sa.String(32), nullable=False, server_default="matched"),
    )
    op.add_column(
        "script_alignments",
        sa.Column("visual_evidence", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
    )
    op.create_table(
        "performance_snapshots",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "publication_id", sa.Uuid(), sa.ForeignKey("content_publications.id"), nullable=False
        ),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reporting_window_days", sa.Integer(), nullable=False),
        sa.Column("views", sa.Integer(), nullable=False),
        sa.Column("likes", sa.Integer()),
        sa.Column("comments", sa.Integer()),
        sa.Column("shares", sa.Integer()),
        sa.Column("retention", sa.Float()),
        sa.Column("source", sa.String(200), nullable=False),
        sa.UniqueConstraint(
            "publication_id",
            "observed_at",
            "reporting_window_days",
            name="uq_performance_observation",
        ),
    )
    op.create_index(
        "ix_performance_snapshots_publication_id", "performance_snapshots", ["publication_id"]
    )


def downgrade():
    op.drop_constraint("fk_platform_render", "platform_exports", type_="foreignkey")
    op.drop_constraint("uq_platform_render", "platform_exports", type_="unique")
    op.drop_column("platform_exports", "render_id")
    op.drop_constraint("fk_candidate_script", "clip_candidates", type_="foreignkey")
    op.drop_column("clip_candidates", "script_version_id")
    op.drop_table("performance_snapshots")
    op.drop_constraint("fk_alignment_script", "script_alignments", type_="foreignkey")
    for name in ("script_version_id", "section_id", "match_status", "visual_evidence"):
        op.drop_column("script_alignments", name)
    op.drop_constraint("fk_render_job", "edit_renders", type_="foreignkey")
    op.drop_constraint("uq_render_job", "edit_renders", type_="unique")
    for name in ("job_id", "preset_name", "platform", "supporting_copy", "recipe_snapshot"):
        op.drop_column("edit_renders", name)
