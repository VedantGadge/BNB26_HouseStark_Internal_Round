"""Create persistence for projects, scripts, conversations, and jobs.

Revision ID: 0001_script_feature_persistence
Revises:
Create Date: 2026-10-03
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0001_script_feature_persistence"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def timestamps() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    ]


def upgrade() -> None:
    op.create_table(
        "ai_script_projects",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("owner_id", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("brief", sa.Text(), nullable=False),
        sa.Column("audience", sa.String(length=500)),
        sa.Column("tone", sa.String(length=120)),
        sa.Column("target_platforms", sa.JSON(), nullable=False),
        sa.Column("workflow_stage", sa.String(length=64), nullable=False),
        sa.Column("current_script_version_id", sa.Uuid()),
        *timestamps(),
    )
    op.create_index("ix_ai_script_projects_owner_id", "ai_script_projects", ["owner_id"])
    op.create_index(
        "ix_ai_script_projects_workflow_stage",
        "ai_script_projects",
        ["workflow_stage"],
    )

    op.create_table(
        "ai_script_jobs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("owner_id", sa.String(length=255), nullable=False),
        sa.Column("project_id", sa.Uuid(), sa.ForeignKey("ai_script_projects.id")),
        sa.Column("type", sa.String(length=64), nullable=False),
        sa.Column("idempotency_key", sa.String(length=200), nullable=False),
        sa.Column("payload_hash", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("stage", sa.String(length=128), nullable=False),
        sa.Column("attempt", sa.Integer(), nullable=False),
        sa.Column("input_snapshot", sa.JSON(), nullable=False),
        sa.Column("routing_snapshot", sa.JSON(), nullable=False),
        sa.Column("graph_thread_id", sa.String(length=255), unique=True),
        sa.Column("error", sa.Text()),
        sa.Column("claimed_at", sa.DateTime(timezone=True)),
        sa.Column("lease_expires_at", sa.DateTime(timezone=True)),
        *timestamps(),
        sa.UniqueConstraint(
            "owner_id",
            "type",
            "idempotency_key",
            name="uq_ai_script_job_owner_type_idempotency_key",
        ),
    )
    op.create_index("ix_ai_script_jobs_owner_id", "ai_script_jobs", ["owner_id"])
    op.create_index("ix_ai_script_jobs_project_id", "ai_script_jobs", ["project_id"])
    op.create_index("ix_ai_script_jobs_type", "ai_script_jobs", ["type"])
    op.create_index("ix_ai_script_jobs_status", "ai_script_jobs", ["status"])

    op.create_table(
        "ai_script_style_profile_revisions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("owner_id", sa.String(length=255), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("profile", sa.JSON(), nullable=False),
        sa.Column("suggestion_id", sa.Uuid()),
        *timestamps(),
        sa.UniqueConstraint(
            "owner_id",
            "revision",
            name="uq_ai_script_style_profile_owner_revision",
        ),
    )
    op.create_index(
        "ix_ai_script_style_profile_revisions_owner_id",
        "ai_script_style_profile_revisions",
        ["owner_id"],
    )

    op.create_table(
        "ai_script_campaign_brief_revisions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("project_id", sa.Uuid(), sa.ForeignKey("ai_script_projects.id"), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("content_mode", sa.String(length=32), nullable=False),
        sa.Column("brand_brief", sa.JSON()),
        *timestamps(),
        sa.UniqueConstraint(
            "project_id",
            "revision",
            name="uq_ai_script_campaign_project_revision",
        ),
    )
    op.create_index(
        "ix_ai_script_campaign_brief_revisions_project_id",
        "ai_script_campaign_brief_revisions",
        ["project_id"],
    )

    op.create_table(
        "ai_script_style_profile_suggestions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("owner_id", sa.String(length=255), nullable=False),
        sa.Column(
            "job_id",
            sa.Uuid(),
            sa.ForeignKey("ai_script_jobs.id"),
            nullable=False,
            unique=True,
        ),
        sa.Column("examples", sa.JSON(), nullable=False),
        sa.Column("profile", sa.JSON()),
        *timestamps(),
    )
    op.create_index(
        "ix_ai_script_style_profile_suggestions_owner_id",
        "ai_script_style_profile_suggestions",
        ["owner_id"],
    )

    op.create_table(
        "ai_script_versions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("project_id", sa.Uuid(), sa.ForeignKey("ai_script_projects.id"), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("parent_version_id", sa.Uuid(), sa.ForeignKey("ai_script_versions.id")),
        sa.Column("job_id", sa.Uuid(), sa.ForeignKey("ai_script_jobs.id"), unique=True),
        sa.Column("origin", sa.String(length=64), nullable=False),
        sa.Column("content", sa.JSON(), nullable=False),
        sa.Column("requirement_checks", sa.JSON(), nullable=False),
        sa.Column("warning_ids", sa.JSON(), nullable=False),
        sa.Column("input_snapshot", sa.JSON(), nullable=False),
        *timestamps(),
        sa.UniqueConstraint("project_id", "version", name="uq_ai_script_project_version"),
    )
    op.create_index("ix_ai_script_versions_project_id", "ai_script_versions", ["project_id"])

    op.create_table(
        "ai_script_assistant_conversations",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("owner_id", sa.String(length=255), nullable=False),
        sa.Column("project_id", sa.Uuid(), sa.ForeignKey("ai_script_projects.id"), nullable=False),
        *timestamps(),
    )
    op.create_index(
        "ix_ai_script_assistant_conversations_owner_id",
        "ai_script_assistant_conversations",
        ["owner_id"],
    )
    op.create_index(
        "ix_ai_script_assistant_conversations_project_id",
        "ai_script_assistant_conversations",
        ["project_id"],
    )

    op.create_table(
        "ai_script_assistant_messages",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "conversation_id",
            sa.Uuid(),
            sa.ForeignKey("ai_script_assistant_conversations.id"),
            nullable=False,
        ),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("target_scope", sa.String(length=32)),
        sa.Column("target_id", sa.String(length=120)),
        sa.Column("base_version", sa.Integer()),
        *timestamps(),
    )
    op.create_index(
        "ix_ai_script_assistant_messages_conversation_id",
        "ai_script_assistant_messages",
        ["conversation_id"],
    )

    op.create_table(
        "ai_script_revision_proposals",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("owner_id", sa.String(length=255), nullable=False),
        sa.Column("project_id", sa.Uuid(), sa.ForeignKey("ai_script_projects.id"), nullable=False),
        sa.Column(
            "conversation_id",
            sa.Uuid(),
            sa.ForeignKey("ai_script_assistant_conversations.id"),
            nullable=False,
        ),
        sa.Column(
            "base_script_version_id",
            sa.Uuid(),
            sa.ForeignKey("ai_script_versions.id"),
            nullable=False,
        ),
        sa.Column(
            "job_id",
            sa.Uuid(),
            sa.ForeignKey("ai_script_jobs.id"),
            nullable=False,
            unique=True,
        ),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("explanation", sa.Text()),
        sa.Column("changes", sa.JSON()),
        sa.Column("requirement_checks", sa.JSON(), nullable=False),
        sa.Column("warning_ids", sa.JSON(), nullable=False),
        *timestamps(),
    )
    op.create_index(
        "ix_ai_script_revision_proposals_owner_id",
        "ai_script_revision_proposals",
        ["owner_id"],
    )
    op.create_index(
        "ix_ai_script_revision_proposals_project_id",
        "ai_script_revision_proposals",
        ["project_id"],
    )
    op.create_index(
        "ix_ai_script_revision_proposals_conversation_id",
        "ai_script_revision_proposals",
        ["conversation_id"],
    )
    op.create_index(
        "ix_ai_script_revision_proposals_base_script_version_id",
        "ai_script_revision_proposals",
        ["base_script_version_id"],
    )
    op.create_index(
        "ix_ai_script_revision_proposals_status",
        "ai_script_revision_proposals",
        ["status"],
    )

    op.create_table(
        "ai_script_llm_calls",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("job_id", sa.Uuid(), sa.ForeignKey("ai_script_jobs.id"), nullable=False),
        sa.Column("attempt", sa.Integer(), nullable=False),
        sa.Column("requested_model", sa.String(length=255), nullable=False),
        sa.Column("actual_model", sa.String(length=255)),
        sa.Column("provider", sa.String(length=255)),
        sa.Column("input_tokens", sa.Integer()),
        sa.Column("output_tokens", sa.Integer()),
        sa.Column("outcome", sa.String(length=64), nullable=False),
        sa.Column("error_category", sa.String(length=64)),
        *timestamps(),
    )
    op.create_index("ix_ai_script_llm_calls_job_id", "ai_script_llm_calls", ["job_id"])


def downgrade() -> None:
    op.drop_table("ai_script_llm_calls")
    op.drop_table("ai_script_revision_proposals")
    op.drop_table("ai_script_assistant_messages")
    op.drop_table("ai_script_assistant_conversations")
    op.drop_table("ai_script_versions")
    op.drop_table("ai_script_style_profile_suggestions")
    op.drop_table("ai_script_campaign_brief_revisions")
    op.drop_table("ai_script_style_profile_revisions")
    op.drop_table("ai_script_jobs")
    op.drop_table("ai_script_projects")
