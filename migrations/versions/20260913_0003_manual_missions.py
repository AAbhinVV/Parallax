"""Manual missions, outbox, audit, and dashboard data.

Revision ID: 20260913_0003
Revises: 20260913_0002
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260913_0003"
down_revision: str | None = "20260913_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

mission_status = postgresql.ENUM(
    "queued",
    "planning",
    "context_collected",
    "waiting_for_approval",
    "running",
    "completed",
    "blocked",
    "rejected",
    "cancelled",
    "partially_complete",
    "failed",
    name="mission_status",
    create_type=False,
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
    mission_status.create(op.get_bind())
    op.add_column(
        "projects", sa.Column("icon", sa.String(50), server_default="folder", nullable=False)
    )
    op.add_column(
        "projects", sa.Column("health_pct", sa.Integer(), server_default="80", nullable=False)
    )
    op.execute(
        """
        INSERT INTO projects (id, workspace_id, name, description, icon, health_pct)
        SELECT gen_random_uuid(), w.id, 'General', 'Default mission project', 'folder', 80
        FROM workspaces w
        WHERE NOT EXISTS (
            SELECT 1 FROM projects p WHERE p.workspace_id = w.id AND p.name = 'General'
        )
        """
    )

    op.create_table(
        "missions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "workspace_id",
            sa.Uuid(),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "created_by_user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "project_id",
            sa.Uuid(),
            sa.ForeignKey("projects.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("project_name", sa.String(120), nullable=False),
        sa.Column("status", mission_status, nullable=False),
        sa.Column("progress_current", sa.Integer(), nullable=False),
        sa.Column("progress_total", sa.Integer(), nullable=False),
        sa.Column("result_summary", sa.Text()),
        sa.Column("correlation_id", sa.Uuid(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        *timestamps(),
    )
    for column in ("workspace_id", "created_by_user_id", "project_id", "correlation_id"):
        op.create_index(f"ix_missions_{column}", "missions", [column])
    op.create_index("ix_missions_workspace_created", "missions", ["workspace_id", "created_at"])
    op.create_index("ix_missions_workspace_status", "missions", ["workspace_id", "status"])

    op.create_table(
        "mission_steps",
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
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("status", sa.String(40), nullable=False),
        sa.Column("detail", sa.Text(), nullable=False),
        *timestamps(),
        sa.UniqueConstraint("mission_id", "sequence", name="uq_mission_step_sequence"),
    )
    op.create_index("ix_mission_steps_workspace_id", "mission_steps", ["workspace_id"])
    op.create_index("ix_mission_steps_mission_id", "mission_steps", ["mission_id"])

    op.create_table(
        "mission_transitions",
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
        sa.Column("from_status", mission_status),
        sa.Column("to_status", mission_status, nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("actor_user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    for column in ("workspace_id", "mission_id", "actor_user_id"):
        op.create_index(f"ix_mission_transitions_{column}", "mission_transitions", [column])
    op.create_index(
        "ix_transition_mission_created", "mission_transitions", ["mission_id", "created_at"]
    )

    op.create_table(
        "activity_records",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "workspace_id",
            sa.Uuid(),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("mission_id", sa.Uuid(), sa.ForeignKey("missions.id", ondelete="CASCADE")),
        sa.Column("icon", sa.String(50), nullable=False),
        sa.Column("title", sa.String(160), nullable=False),
        sa.Column("detail", sa.Text(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_activity_records_workspace_id", "activity_records", ["workspace_id"])
    op.create_index("ix_activity_records_mission_id", "activity_records", ["mission_id"])
    op.create_index(
        "ix_activity_workspace_created", "activity_records", ["workspace_id", "created_at"]
    )

    op.create_table(
        "audit_events",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "workspace_id",
            sa.Uuid(),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("actor_user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("mission_id", sa.Uuid(), sa.ForeignKey("missions.id", ondelete="CASCADE")),
        sa.Column("event_type", sa.String(120), nullable=False),
        sa.Column("correlation_id", sa.Uuid(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    for column in ("workspace_id", "actor_user_id", "mission_id", "event_type", "correlation_id"):
        op.create_index(f"ix_audit_events_{column}", "audit_events", [column])
    op.create_index("ix_audit_workspace_created", "audit_events", ["workspace_id", "created_at"])

    op.create_table(
        "idempotency_records",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "workspace_id",
            sa.Uuid(),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("key", sa.String(128), nullable=False),
        sa.Column("request_hash", sa.String(64), nullable=False),
        sa.Column("resource_type", sa.String(50), nullable=False),
        sa.Column("resource_id", sa.Uuid(), nullable=False),
        *timestamps(),
        sa.UniqueConstraint("workspace_id", "key", name="uq_idempotency_workspace_key"),
    )
    op.create_index("ix_idempotency_records_workspace_id", "idempotency_records", ["workspace_id"])

    op.create_table(
        "outbox_jobs",
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
        sa.Column("job_type", sa.String(80), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("dispatched_at", sa.DateTime(timezone=True)),
        sa.Column("last_error", sa.Text()),
        *timestamps(),
    )
    op.create_index("ix_outbox_jobs_workspace_id", "outbox_jobs", ["workspace_id"])
    op.create_index("ix_outbox_jobs_mission_id", "outbox_jobs", ["mission_id"])
    op.create_index("ix_outbox_status_created", "outbox_jobs", ["status", "created_at"])


def downgrade() -> None:
    for table in (
        "outbox_jobs",
        "idempotency_records",
        "audit_events",
        "activity_records",
        "mission_transitions",
        "mission_steps",
        "missions",
    ):
        op.drop_table(table)
    op.drop_column("projects", "health_pct")
    op.drop_column("projects", "icon")
    mission_status.drop(op.get_bind())
