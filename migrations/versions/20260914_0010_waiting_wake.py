"""Waiting/wake state and connector capabilities for continuous missions.

Revision ID: 20260914_0010
Revises: 20260914_0009
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260914_0010"
down_revision: str | None = "20260914_0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER TYPE mission_status ADD VALUE IF NOT EXISTS 'waiting_for_event'")


def downgrade() -> None:
    # PostgreSQL cannot remove enum values; the value stays unused.
    pass
