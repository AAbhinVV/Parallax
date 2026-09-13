import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from parallax_backend.database import get_session
from parallax_backend.dependencies import RequestIdentity, get_current_identity, require_roles
from parallax_backend.models import User, WorkspaceMembership, WorkspaceRole
from parallax_backend.schemas import ErrorResponse, MemberRead, MemberRoleUpdate, WorkspaceSummary

router = APIRouter(prefix="/api/workspaces", tags=["workspaces"])
ERRORS: dict[int | str, dict[str, Any]] = {
    401: {"model": ErrorResponse},
    403: {"model": ErrorResponse},
}


@router.get(
    "/current", response_model=WorkspaceSummary, responses=ERRORS, summary="Current workspace"
)
async def current_workspace(
    identity: RequestIdentity = Depends(get_current_identity),
) -> WorkspaceSummary:
    return WorkspaceSummary(
        id=identity.workspace.id,
        name=identity.workspace.name,
        slug=identity.workspace.slug,
        role=identity.membership.role,
    )


@router.get(
    "/current/members",
    response_model=list[MemberRead],
    responses=ERRORS,
    summary="List current workspace members",
)
async def list_members(
    identity: RequestIdentity = Depends(get_current_identity),
    session: AsyncSession = Depends(get_session),
) -> list[MemberRead]:
    rows = (
        await session.execute(
            select(WorkspaceMembership, User)
            .join(User, User.id == WorkspaceMembership.user_id)
            .where(WorkspaceMembership.workspace_id == identity.workspace.id)
            .order_by(User.display_name)
        )
    ).all()
    return [
        MemberRead(
            user_id=user.id,
            email=user.email,
            display_name=user.display_name,
            role=membership.role,
        )
        for membership, user in rows
    ]


@router.patch(
    "/current/members/{user_id}",
    response_model=MemberRead,
    responses={**ERRORS, 404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}},
    summary="Change a member role",
)
async def update_member_role(
    user_id: uuid.UUID,
    payload: MemberRoleUpdate,
    identity: RequestIdentity = Depends(require_roles(WorkspaceRole.OWNER, WorkspaceRole.ADMIN)),
    session: AsyncSession = Depends(get_session),
) -> MemberRead:
    row = (
        await session.execute(
            select(WorkspaceMembership, User)
            .join(User, User.id == WorkspaceMembership.user_id)
            .where(
                WorkspaceMembership.workspace_id == identity.workspace.id,
                WorkspaceMembership.user_id == user_id,
            )
        )
    ).one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Workspace member not found")
    membership, user = row
    if identity.membership.role != WorkspaceRole.OWNER and (
        membership.role == WorkspaceRole.OWNER or payload.role == WorkspaceRole.OWNER
    ):
        raise HTTPException(status_code=403, detail="Only owners can manage the owner role")
    if membership.role == WorkspaceRole.OWNER and payload.role != WorkspaceRole.OWNER:
        owner_count = await session.scalar(
            select(func.count())
            .select_from(WorkspaceMembership)
            .where(
                WorkspaceMembership.workspace_id == identity.workspace.id,
                WorkspaceMembership.role == WorkspaceRole.OWNER,
            )
        )
        if owner_count == 1:
            raise HTTPException(status_code=409, detail="A workspace must retain an owner")
    membership.role = payload.role
    await session.commit()
    return MemberRead(
        user_id=user.id,
        email=user.email,
        display_name=user.display_name,
        role=membership.role,
    )
