"""Identity, workspaces, and core data.

Revision ID: 20260913_0002
Revises: 20260913_0001
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260913_0002"
down_revision: str | None = "20260913_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

workspace_role = postgresql.ENUM(
    "owner", "admin", "manager", "reviewer", "viewer", name="workspace_role", create_type=False
)
integration_provider = postgresql.ENUM(
    "github", "jira", "notion", "slack", name="integration_provider", create_type=False
)
integration_status = postgresql.ENUM(
    "disconnected", "connected", "error", name="integration_status", create_type=False
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
    bind = op.get_bind()
    postgresql.ENUM(
        "owner", "admin", "manager", "reviewer", "viewer", name="workspace_role"
    ).create(bind)
    postgresql.ENUM("github", "jira", "notion", "slack", name="integration_provider").create(bind)
    postgresql.ENUM("disconnected", "connected", "error", name="integration_status").create(bind)

    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("display_name", sa.String(120), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        *timestamps(),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "workspaces",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("slug", sa.String(80), nullable=False),
        *timestamps(),
        sa.UniqueConstraint("slug", name="uq_workspaces_slug"),
    )
    op.create_index("ix_workspaces_slug", "workspaces", ["slug"], unique=True)

    op.create_table(
        "workspace_memberships",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "workspace_id",
            sa.Uuid(),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("role", workspace_role, nullable=False),
        *timestamps(),
        sa.UniqueConstraint("workspace_id", "user_id", name="uq_membership_workspace_user"),
    )
    op.create_index(
        "ix_workspace_memberships_workspace_id", "workspace_memberships", ["workspace_id"]
    )
    op.create_index("ix_workspace_memberships_user_id", "workspace_memberships", ["user_id"])
    op.create_index(
        "ix_membership_user_workspace", "workspace_memberships", ["user_id", "workspace_id"]
    )

    op.create_table(
        "teams",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "workspace_id",
            sa.Uuid(),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("description", sa.Text()),
        *timestamps(),
        sa.UniqueConstraint("workspace_id", "name", name="uq_team_workspace_name"),
    )
    op.create_index("ix_teams_workspace_id", "teams", ["workspace_id"])

    op.create_table(
        "projects",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "workspace_id",
            sa.Uuid(),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("team_id", sa.Uuid(), sa.ForeignKey("teams.id", ondelete="SET NULL")),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("description", sa.Text()),
        *timestamps(),
        sa.UniqueConstraint("workspace_id", "name", name="uq_project_workspace_name"),
    )
    op.create_index("ix_projects_workspace_id", "projects", ["workspace_id"])
    op.create_index("ix_projects_team_id", "projects", ["team_id"])

    op.create_table(
        "repositories",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "workspace_id",
            sa.Uuid(),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("project_id", sa.Uuid(), sa.ForeignKey("projects.id", ondelete="SET NULL")),
        sa.Column("provider", integration_provider, nullable=False),
        sa.Column("external_id", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("default_branch", sa.String(255), nullable=False),
        *timestamps(),
        sa.UniqueConstraint(
            "workspace_id", "provider", "external_id", name="uq_repository_external"
        ),
    )
    op.create_index("ix_repositories_workspace_id", "repositories", ["workspace_id"])
    op.create_index("ix_repositories_project_id", "repositories", ["project_id"])

    op.create_table(
        "integrations",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "workspace_id",
            sa.Uuid(),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("provider", integration_provider, nullable=False),
        sa.Column("status", integration_status, nullable=False),
        sa.Column("display_name", sa.String(120), nullable=False),
        sa.Column("configuration", sa.JSON(), nullable=False),
        sa.Column("credential_reference", sa.String(255)),
        sa.Column("last_checked_at", sa.DateTime(timezone=True)),
        *timestamps(),
        sa.UniqueConstraint("workspace_id", "provider", name="uq_integration_workspace_provider"),
    )
    op.create_index("ix_integrations_workspace_id", "integrations", ["workspace_id"])

    op.create_table(
        "external_identities",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "workspace_id",
            sa.Uuid(),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("provider", integration_provider, nullable=False),
        sa.Column("external_user_id", sa.String(255), nullable=False),
        sa.Column("external_username", sa.String(255)),
        *timestamps(),
        sa.UniqueConstraint(
            "workspace_id", "provider", "external_user_id", name="uq_external_identity"
        ),
    )
    op.create_index("ix_external_identities_workspace_id", "external_identities", ["workspace_id"])
    op.create_index("ix_external_identities_user_id", "external_identities", ["user_id"])

    op.create_table(
        "refresh_sessions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column(
            "workspace_id",
            sa.Uuid(),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        sa.Column(
            "replaced_by_session_id",
            sa.Uuid(),
            sa.ForeignKey("refresh_sessions.id", ondelete="SET NULL"),
        ),
        *timestamps(),
        sa.UniqueConstraint("token_hash", name="uq_refresh_sessions_token_hash"),
    )
    op.create_index("ix_refresh_sessions_user_id", "refresh_sessions", ["user_id"])
    op.create_index("ix_refresh_sessions_workspace_id", "refresh_sessions", ["workspace_id"])
    op.create_index(
        "ix_refresh_sessions_token_hash", "refresh_sessions", ["token_hash"], unique=True
    )
    op.create_index("ix_refresh_sessions_expires_at", "refresh_sessions", ["expires_at"])


def downgrade() -> None:
    for table in (
        "refresh_sessions",
        "external_identities",
        "integrations",
        "repositories",
        "projects",
        "teams",
        "workspace_memberships",
        "workspaces",
        "users",
    ):
        op.drop_table(table)
    integration_status.drop(op.get_bind())
    integration_provider.drop(op.get_bind())
    workspace_role.drop(op.get_bind())
