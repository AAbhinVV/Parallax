"""Typed proposals, policy results, and approval bundles.

Revision ID: 20260913_0005
Revises: 20260913_0004
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260913_0005"
down_revision: str | None = "20260913_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

provider = postgresql.ENUM(
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
        "approval_bundles",
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
            "assessment_id",
            sa.Uuid(),
            sa.ForeignKey("agent_assessments.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("policy_result", sa.JSON(), nullable=False),
        sa.Column("decided_by_user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("decided_at", sa.DateTime(timezone=True)),
        sa.Column("decision_note", sa.Text()),
        *timestamps(),
        sa.UniqueConstraint("mission_id", "version", name="uq_approval_bundle_version"),
    )
    for column in ("workspace_id", "mission_id", "assessment_id", "decided_by_user_id"):
        op.create_index(f"ix_approval_bundles_{column}", "approval_bundles", [column])

    op.create_table(
        "action_proposals",
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
            "approval_bundle_id",
            sa.Uuid(),
            sa.ForeignKey("approval_bundles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("provider", provider, nullable=False),
        sa.Column("operation", sa.String(120), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("citations", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        *timestamps(),
        sa.UniqueConstraint("approval_bundle_id", "sequence", name="uq_action_sequence"),
    )
    for column in ("workspace_id", "mission_id", "approval_bundle_id"):
        op.create_index(f"ix_action_proposals_{column}", "action_proposals", [column])


def downgrade() -> None:
    op.drop_table("action_proposals")
    op.drop_table("approval_bundles")
