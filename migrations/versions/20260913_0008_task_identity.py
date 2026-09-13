"""Task identity and verified completion proofs.

Revision ID: 20260913_0008
Revises: 20260913_0007
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260913_0008"
down_revision: str | None = "20260913_0007"
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
    op.add_column(
        "missions",
        sa.Column("task_fingerprint", sa.String(length=64), nullable=True),
    )
    op.create_index("ix_missions_task_fingerprint", "missions", ["task_fingerprint"])
    op.create_table(
        "mission_completion_proofs",
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
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("actions", sa.JSON(), nullable=False),
        sa.Column("verification_ids", sa.JSON(), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("mission_id", name="uq_completion_proof_mission"),
        *timestamps(),
    )
    op.create_index(
        "ix_completion_proof_workspace_id", "mission_completion_proofs", ["workspace_id"]
    )
    op.create_index("ix_completion_proof_mission_id", "mission_completion_proofs", ["mission_id"])


def downgrade() -> None:
    op.drop_table("mission_completion_proofs")
    op.drop_index("ix_missions_task_fingerprint", table_name="missions")
    op.drop_column("missions", "task_fingerprint")
