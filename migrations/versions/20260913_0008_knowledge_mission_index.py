"""Add the missing knowledge fact mission lookup index.

Revision ID: 20260913_0008
Revises: 20260913_0007
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260913_0008"
down_revision: str | None = "20260913_0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index("ix_knowledge_facts_mission_id", "knowledge_facts", ["mission_id"])


def downgrade() -> None:
    op.drop_index("ix_knowledge_facts_mission_id", table_name="knowledge_facts")
