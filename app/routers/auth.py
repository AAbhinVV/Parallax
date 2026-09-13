from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.dependencies import RequestIdentity, get_current_identity
from app.models import (
    Integration,
    IntegrationProvider,
    IntegrationStatus,
    Project,
    User,
    Workspace,
    WorkspaceMembership,
    WorkspaceRole,
)
from app.schemas import (
    ErrorResponse,
    LoginRequest,
    LogoutRequest,
    MeResponse,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserRead,
    WorkspaceRead,
)
from app.security import hash_password, verify_password
from app.services.auth import find_valid_refresh_session, issue_token_pair, membership_for_login

router = APIRouter(prefix="/api/auth", tags=["authentication"])
ERRORS: dict[int | str, dict[str, Any]] = {
    400: {"model": ErrorResponse},
    401: {"model": ErrorResponse},
    403: {"model": ErrorResponse},
    409: {"model": ErrorResponse},
    422: {"description": "Request validation failed"},
}


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    responses=ERRORS,
    summary="Register an owner and workspace",
)
async def register(
    payload: RegisterRequest, session: AsyncSession = Depends(get_session)
) -> TokenResponse:
    """Create a local user, a new workspace, and its owner membership atomically."""
    user = User(
        email=str(payload.email),
        password_hash=hash_password(payload.password),
        display_name=payload.display_name.strip(),
    )
    workspace = Workspace(name=payload.workspace_name.strip(), slug=payload.workspace_slug)
    session.add_all([user, workspace])
    try:
        await session.flush()
        session.add(
            WorkspaceMembership(
                workspace_id=workspace.id,
                user_id=user.id,
                role=WorkspaceRole.OWNER,
            )
        )
        session.add_all(
            [
                Integration(
                    workspace_id=workspace.id,
                    provider=provider,
                    status=IntegrationStatus.DISCONNECTED,
                    display_name=provider.value.title(),
                    configuration={},
                )
                for provider in IntegrationProvider
            ]
        )
        session.add(
            Project(
                workspace_id=workspace.id,
                name="General",
                description="Default mission project",
                icon="folder",
                health_pct=80,
            )
        )
        tokens = await issue_token_pair(session, user, workspace)
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(
            status_code=409, detail="Email or workspace slug already exists"
        ) from None
    return tokens


@router.post("/login", response_model=TokenResponse, responses=ERRORS, summary="Log in locally")
async def login(
    payload: LoginRequest, session: AsyncSession = Depends(get_session)
) -> TokenResponse:
    user = (
        await session.execute(select(User).where(User.email == str(payload.email)))
    ).scalar_one_or_none()
    if (
        user is None
        or not user.is_active
        or not verify_password(payload.password, user.password_hash)
    ):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    _, workspace = await membership_for_login(session, user.id, payload.workspace_id)
    tokens = await issue_token_pair(session, user, workspace)
    await session.commit()
    return tokens


@router.post(
    "/refresh", response_model=TokenResponse, responses=ERRORS, summary="Rotate a refresh token"
)
async def refresh(
    payload: RefreshRequest, session: AsyncSession = Depends(get_session)
) -> TokenResponse:
    current, user, workspace = await find_valid_refresh_session(
        session, payload.refresh_token, for_update=True
    )
    tokens = await issue_token_pair(session, user, workspace, replacing=current)
    await session.commit()
    return tokens


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={401: {"model": ErrorResponse}, 422: {"description": "Request validation failed"}},
    summary="Revoke a refresh session",
)
async def logout(payload: LogoutRequest, session: AsyncSession = Depends(get_session)) -> Response:
    refresh_session, _, _ = await find_valid_refresh_session(
        session, payload.refresh_token, for_update=True
    )
    refresh_session.revoked_at = datetime.now(UTC)
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/me", response_model=MeResponse, responses=ERRORS, summary="Get the current identity")
async def me(
    identity: RequestIdentity = Depends(get_current_identity),
    session: AsyncSession = Depends(get_session),
) -> MeResponse:
    rows = (
        await session.execute(
            select(WorkspaceMembership, Workspace)
            .join(Workspace, Workspace.id == WorkspaceMembership.workspace_id)
            .where(WorkspaceMembership.user_id == identity.user.id)
            .order_by(Workspace.name)
        )
    ).all()
    workspaces = [
        WorkspaceRead(
            id=workspace.id, name=workspace.name, slug=workspace.slug, role=membership.role
        )
        for membership, workspace in rows
    ]
    return MeResponse(
        user=UserRead.model_validate(identity.user),
        current_workspace=WorkspaceRead(
            id=identity.workspace.id,
            name=identity.workspace.name,
            slug=identity.workspace.slug,
            role=identity.membership.role,
        ),
        workspaces=workspaces,
    )
