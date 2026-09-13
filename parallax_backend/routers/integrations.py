from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from parallax_backend.config import settings
from parallax_backend.database import get_session
from parallax_backend.dependencies import RequestIdentity, get_current_identity, require_roles
from parallax_backend.integrations.contracts import AdapterError
from parallax_backend.integrations.registry import build_adapter
from parallax_backend.models import (
    AuditEvent,
    Integration,
    IntegrationProvider,
    IntegrationStatus,
    WorkspaceRole,
)
from parallax_backend.schemas import (
    ErrorResponse,
    IntegrationCapabilitiesRead,
    IntegrationCapabilityRead,
    IntegrationStatusRead,
)

router = APIRouter(prefix="/api/integrations", tags=["integrations"])
ERRORS: dict[int | str, dict[str, Any]] = {
    401: {"model": ErrorResponse},
    403: {"model": ErrorResponse},
    404: {"model": ErrorResponse},
    502: {"model": ErrorResponse},
}
DISPLAY = {
    IntegrationProvider.GITHUB: "GitHub",
    IntegrationProvider.JIRA: "Jira",
    IntegrationProvider.NOTION: "Notion",
    IntegrationProvider.SLACK: "Slack",
}


@router.get(
    "", response_model=list[IntegrationStatusRead], responses=ERRORS, summary="Integrations"
)
async def integrations(
    identity: RequestIdentity = Depends(get_current_identity),
    session: AsyncSession = Depends(get_session),
) -> list[IntegrationStatusRead]:
    records = (
        await session.execute(
            select(Integration).where(Integration.workspace_id == identity.workspace.id)
        )
    ).scalars()
    by_provider = {record.provider: record for record in records}
    return [
        IntegrationStatusRead(
            name=DISPLAY[provider],
            connected=(record := by_provider.get(provider)) is not None
            and record.status == IntegrationStatus.CONNECTED,
            detail=(record.configuration.get("last_message") if record else None)
            or (record.display_name if record else "Not configured"),
        )
        for provider in IntegrationProvider
    ]


@router.get(
    "/{provider}/capabilities",
    response_model=IntegrationCapabilitiesRead,
    responses=ERRORS,
    summary="Describe integration capabilities",
)
async def capabilities(
    provider: IntegrationProvider,
    _: RequestIdentity = Depends(get_current_identity),
) -> IntegrationCapabilitiesRead:
    adapter = build_adapter(provider)
    try:
        return IntegrationCapabilitiesRead(
            name=DISPLAY[provider],
            mode=settings.integration_mode,
            capabilities=[
                IntegrationCapabilityRead(
                    operation=item.operation,
                    access=item.access,
                    description=item.description,
                )
                for item in adapter.capabilities
            ],
        )
    finally:
        await adapter.close()


@router.post(
    "/{provider}/check",
    response_model=IntegrationStatusRead,
    responses=ERRORS,
    summary="Check an integration connection",
)
async def check_integration(
    provider: IntegrationProvider,
    request: Request,
    identity: RequestIdentity = Depends(
        require_roles(WorkspaceRole.OWNER, WorkspaceRole.ADMIN, WorkspaceRole.MANAGER)
    ),
    session: AsyncSession = Depends(get_session),
) -> IntegrationStatusRead:
    record = (
        await session.execute(
            select(Integration).where(
                Integration.workspace_id == identity.workspace.id,
                Integration.provider == provider,
            )
        )
    ).scalar_one_or_none()
    if record is None:
        raise HTTPException(status_code=404, detail="Integration not found")
    adapter = build_adapter(provider)
    try:
        health = await adapter.health()
    except AdapterError as exc:
        record.status = IntegrationStatus.ERROR
        record.configuration = {**record.configuration, "last_message": str(exc)}
        await session.commit()
        raise HTTPException(status_code=502, detail=str(exc)) from None
    finally:
        await adapter.close()
    record.status = (
        IntegrationStatus.CONNECTED if health.connected else IntegrationStatus.DISCONNECTED
    )
    record.last_checked_at = health.checked_at
    record.configuration = {
        **record.configuration,
        "mode": settings.integration_mode,
        "last_message": health.detail,
    }
    session.add(
        AuditEvent(
            workspace_id=identity.workspace.id,
            actor_user_id=identity.user.id,
            mission_id=None,
            event_type="integration.connection_checked",
            correlation_id=request.state.correlation_id,
            payload={
                "provider": provider.value,
                "connected": health.connected,
                "mode": settings.integration_mode,
            },
        )
    )
    await session.commit()
    return IntegrationStatusRead(
        name=DISPLAY[provider], connected=health.connected, detail=health.detail
    )
