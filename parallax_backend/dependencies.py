import uuid
from collections.abc import Callable, Coroutine
from dataclasses import dataclass
from typing import Any

import jwt
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from parallax_backend.database import get_session
from parallax_backend.models import (
    RefreshSession,
    User,
    Workspace,
    WorkspaceMembership,
    WorkspaceRole,
)
from parallax_backend.security import decode_access_token

bearer_scheme = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class RequestIdentity:
    user: User
    workspace: Workspace
    membership: WorkspaceMembership
    session: RefreshSession


async def get_current_identity(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    workspace_header: str | None = Header(default=None, alias="X-Workspace-ID"),
    session: AsyncSession = Depends(get_session),
) -> RequestIdentity:
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired authentication token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credentials is None:
        raise unauthorized
    try:
        claims = decode_access_token(credentials.credentials)
    except (jwt.InvalidTokenError, ValueError, KeyError):
        raise unauthorized from None

    if workspace_header is not None:
        try:
            requested_workspace = uuid.UUID(workspace_header)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid X-Workspace-ID") from None
        if requested_workspace != claims.workspace_id:
            raise HTTPException(status_code=403, detail="Token is not scoped to this workspace")

    result = await session.execute(
        select(User, Workspace, WorkspaceMembership, RefreshSession)
        .join(WorkspaceMembership, WorkspaceMembership.user_id == User.id)
        .join(Workspace, Workspace.id == WorkspaceMembership.workspace_id)
        .join(RefreshSession, RefreshSession.user_id == User.id)
        .where(
            User.id == claims.user_id,
            User.is_active.is_(True),
            Workspace.id == claims.workspace_id,
            RefreshSession.id == claims.session_id,
            RefreshSession.workspace_id == claims.workspace_id,
            RefreshSession.revoked_at.is_(None),
        )
    )
    row = result.one_or_none()
    if row is None:
        raise unauthorized
    user, workspace, membership, refresh_session = row
    return RequestIdentity(user, workspace, membership, refresh_session)


def require_roles(
    *allowed: WorkspaceRole,
) -> Callable[..., Coroutine[Any, Any, RequestIdentity]]:
    async def dependency(
        identity: RequestIdentity = Depends(get_current_identity),
    ) -> RequestIdentity:
        if identity.membership.role not in allowed:
            raise HTTPException(status_code=403, detail="Insufficient workspace role")
        return identity

    return dependency
