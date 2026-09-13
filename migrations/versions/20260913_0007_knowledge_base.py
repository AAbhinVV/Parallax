"""Mission knowledge base with provenance lifecycle.

Revision ID: 20260913_0007
Revises: 20260913_0006
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260913_0007"
down_revision: str | None = "20260913_0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


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
        "knowledge_facts",
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
            "kind",
            sa.Enum("source_fact", "decision", name="knowledge_fact_kind"),
            nullable=False,
        ),
        sa.Column(
            "source",
            sa.Enum("github", "jira", "notion", "slack", "agent", name="knowledge_source"),
            nullable=False,
        ),
        sa.Column("source_ref", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("fact", sa.Text(), nullable=False),
        sa.Column("data", sa.JSON(), nullable=False),
        sa.Column(
            "observed_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                "observed",
                "verified",
                "superseded",
                "conflicted",
                name="knowledge_fact_status",
            ),
            nullable=False,
        ),
        sa.Column(
            "superseded_by_id",
            sa.Uuid(),
            sa.ForeignKey("knowledge_facts.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "agent_run_id",
            sa.Uuid(),
            sa.ForeignKey("agent_runs.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("confidence", sa.Float(), nullable=True),
        *timestamps(),
    )
    op.create_index(
        "ix_knowledge_facts_workspace_id", "knowledge_facts", ["workspace_id"]
    )
    op.create_index(
        "ix_knowledge_facts_mission_status", "knowledge_facts", ["mission_id", "status"]
    )
    op.create_index(
        "ix_knowledge_facts_mission_subject",
        "knowledge_facts",
        ["mission_id", "kind", "source", "source_ref"],
    )


def downgrade() -> None:
    op.drop_table("knowledge_facts")
