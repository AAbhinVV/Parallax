import uuid
from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from parallax_backend.config import settings
from parallax_backend.models import RefreshSession, User, Workspace, WorkspaceMembership
from parallax_backend.schemas import TokenResponse
from parallax_backend.security import (
    create_access_token,
    hash_refresh_token,
    new_refresh_token,
    refresh_expiry,
)


async def issue_token_pair(
    session: AsyncSession,
    user: User,
    workspace: Workspace,
    *,
    replacing: RefreshSession | None = None,
) -> TokenResponse:
    raw_refresh_token = new_refresh_token()
    refresh_session = RefreshSession(
        user_id=user.id,
        workspace_id=workspace.id,
        token_hash=hash_refresh_token(raw_refresh_token),
        expires_at=refresh_expiry(),
    )
    session.add(refresh_session)
    await session.flush()
    if replacing is not None:
        replacing.revoked_at = datetime.now(UTC)
        replacing.replaced_by_session_id = refresh_session.id
    access_token, expires_in = create_access_token(user.id, workspace.id, refresh_session.id)
    return TokenResponse(
        access_token=access_token,
        refresh_token=raw_refresh_token,
        expires_in=expires_in,
        workspace_id=workspace.id,
    )


async def find_valid_refresh_session(
    session: AsyncSession, raw_token: str, *, for_update: bool = False
) -> tuple[RefreshSession, User, Workspace]:
    statement = (
        select(RefreshSession, User, Workspace)
        .join(User, User.id == RefreshSession.user_id)
        .join(Workspace, Workspace.id == RefreshSession.workspace_id)
        .where(RefreshSession.token_hash == hash_refresh_token(raw_token))
    )
    if for_update:
        statement = statement.with_for_update()
    row = (await session.execute(statement)).one_or_none()
    if row is None:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    refresh_session, user, workspace = row
    expires_at = refresh_session.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    if (
        refresh_session.revoked_at is not None
        or expires_at <= datetime.now(UTC)
        or not user.is_active
    ):
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    return refresh_session, user, workspace


async def membership_for_login(
    session: AsyncSession, user_id: uuid.UUID, workspace_id: uuid.UUID | None
) -> tuple[WorkspaceMembership, Workspace]:
    statement = (
        select(WorkspaceMembership, Workspace)
        .join(Workspace, Workspace.id == WorkspaceMembership.workspace_id)
        .where(WorkspaceMembership.user_id == user_id)
        .order_by(WorkspaceMembership.created_at)
    )
    if workspace_id is not None:
        statement = statement.where(WorkspaceMembership.workspace_id == workspace_id)
    row = (await session.execute(statement)).first()
    if row is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Workspace access denied")
    return row[0], row[1]


def refresh_cookie_max_age() -> int:
    return settings.jwt_refresh_token_days * 24 * 60 * 60
