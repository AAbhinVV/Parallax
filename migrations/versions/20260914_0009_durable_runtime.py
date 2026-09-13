"""Durable mission runtime: worker leases and step retry state.

Revision ID: 20260914_0009
Revises: 20260913_0008
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260914_0009"
down_revision: str | None = "20260913_0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("missions", sa.Column("worker_id", sa.String(length=120), nullable=True))
    op.add_column(
        "missions", sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.create_index("ix_missions_lease_expires_at", "missions", ["lease_expires_at"])
    op.add_column(
        "mission_steps",
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column("mission_steps", sa.Column("last_error", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("mission_steps", "last_error")
    op.drop_column("mission_steps", "attempts")
    op.drop_index("ix_missions_lease_expires_at", table_name="missions")
    op.drop_column("missions", "lease_expires_at")
    op.drop_column("missions", "worker_id")
