"""Phase 1 foundation metadata table.

Revision ID: 20260913_0001
Revises: None
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260913_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # The original TypeScript Phase-1 scaffold created this table before Alembic
    # was introduced. Keep the migration safe for an existing local Docker volume.
    if not sa.inspect(op.get_bind()).has_table("system_metadata"):
        op.create_table(
            "system_metadata",
            sa.Column("key", sa.Text(), primary_key=True),
            sa.Column("value", sa.JSON(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )


def downgrade() -> None:
    op.drop_table("system_metadata")
