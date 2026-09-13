"""Context evidence and validated Agent assessments.

Revision ID: 20260913_0004
Revises: 20260913_0003
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260913_0004"
down_revision: str | None = "20260913_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

integration_provider = postgresql.ENUM(
    "github", "jira", "notion", "slack", name="integration_provider", create_type=False
)


def timestamps() -> list[sa.Column]:
    return [
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    ]


def upgrade() -> None:
    op.create_table(
        "context_packs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "workspace_id",
            sa.Uuid(),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "mission_id",
            sa.Uuid(),
            sa.ForeignKey("missions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("content", sa.JSON(), nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),
        *timestamps(),
        sa.UniqueConstraint("mission_id", "version", name="uq_context_pack_version"),
    )
    op.create_index("ix_context_packs_workspace_id", "context_packs", ["workspace_id"])
    op.create_index("ix_context_packs_mission_id", "context_packs", ["mission_id"])

    op.create_table(
        "evidence_items",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "workspace_id",
            sa.Uuid(),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "context_pack_id",
            sa.Uuid(),
            sa.ForeignKey("context_packs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("key", sa.String(255), nullable=False),
        sa.Column("provider", integration_provider, nullable=False),
        sa.Column("external_id", sa.String(255), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("url", sa.Text()),
        sa.Column("excerpt", sa.Text(), nullable=False),
        sa.Column("data", sa.JSON(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.UniqueConstraint("context_pack_id", "key", name="uq_evidence_context_key"),
    )
    op.create_index("ix_evidence_items_workspace_id", "evidence_items", ["workspace_id"])
    op.create_index("ix_evidence_items_context_pack_id", "evidence_items", ["context_pack_id"])

    op.create_table(
        "agent_runs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "workspace_id",
            sa.Uuid(),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "mission_id",
            sa.Uuid(),
            sa.ForeignKey("missions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "context_pack_id",
            sa.Uuid(),
            sa.ForeignKey("context_packs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("mode", sa.String(30), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("request_payload", sa.JSON(), nullable=False),
        sa.Column("response_payload", sa.JSON()),
        sa.Column("error", sa.Text()),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_agent_runs_workspace_id", "agent_runs", ["workspace_id"])
    op.create_index("ix_agent_runs_mission_id", "agent_runs", ["mission_id"])
    op.create_index("ix_agent_runs_context_pack_id", "agent_runs", ["context_pack_id"])
    op.create_index("ix_agent_run_mission_created", "agent_runs", ["mission_id", "created_at"])

    op.create_table(
        "agent_assessments",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "workspace_id",
            sa.Uuid(),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "mission_id",
            sa.Uuid(),
            sa.ForeignKey("missions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "agent_run_id",
            sa.Uuid(),
            sa.ForeignKey("agent_runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("context_summary", sa.Text(), nullable=False),
        sa.Column("risk_level", sa.String(20), nullable=False),
        sa.Column("risk_factors", sa.JSON(), nullable=False),
        sa.Column("review_effort_minutes", sa.Integer(), nullable=False),
        sa.Column("effort_rationale", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column("reviewer_candidates", sa.JSON(), nullable=False),
        sa.Column("citations", sa.JSON(), nullable=False),
        sa.Column("proposals", sa.JSON(), nullable=False),
        *timestamps(),
        sa.UniqueConstraint("mission_id", name="uq_agent_assessment_mission"),
    )
    op.create_index("ix_agent_assessments_workspace_id", "agent_assessments", ["workspace_id"])
    op.create_index("ix_agent_assessments_mission_id", "agent_assessments", ["mission_id"])
    op.create_index(
        "ix_agent_assessments_agent_run_id",
        "agent_assessments",
        ["agent_run_id"],
        unique=True,
    )


def downgrade() -> None:
    for table in ("agent_assessments", "agent_runs", "evidence_items", "context_packs"):
        op.drop_table(table)
