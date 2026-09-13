import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from parallax_backend.database import get_session
from parallax_backend.dependencies import RequestIdentity, get_current_identity, require_roles
from parallax_backend.models import (
    ActionProposal,
    ExecutionRecord,
    Mission,
    MissionStatus,
    OutboxJob,
    VerificationRecord,
    WorkspaceRole,
)
from parallax_backend.schemas import ErrorResponse, ExecutionRead, VerificationRead
from parallax_backend.services.missions import record_mission_event, transition_mission

router = APIRouter(prefix="/api/missions", tags=["execution"])
ERRORS: dict[int | str, dict[str, Any]] = {
    401: {"model": ErrorResponse},
    403: {"model": ErrorResponse},
    404: {"model": ErrorResponse},
    409: {"model": ErrorResponse},
}
Operator = Annotated[
    RequestIdentity,
    Depends(require_roles(WorkspaceRole.OWNER, WorkspaceRole.ADMIN, WorkspaceRole.MANAGER)),
]


@router.get(
    "/{mission_id}/executions",
    response_model=list[ExecutionRead],
    responses=ERRORS,
    summary="List action executions and verification",
)
async def list_executions(
    mission_id: uuid.UUID,
    identity: RequestIdentity = Depends(get_current_identity),
    session: AsyncSession = Depends(get_session),
) -> list[ExecutionRead]:
    rows = (
        await session.execute(
            select(ExecutionRecord, ActionProposal, VerificationRecord)
            .join(ActionProposal, ActionProposal.id == ExecutionRecord.action_proposal_id)
            .outerjoin(VerificationRecord, VerificationRecord.execution_id == ExecutionRecord.id)
            .where(
                ExecutionRecord.mission_id == mission_id,
                ExecutionRecord.workspace_id == identity.workspace.id,
            )
            .order_by(ActionProposal.sequence)
        )
    ).all()
    return [
        ExecutionRead(
            id=execution.id,
            action_proposal_id=execution.action_proposal_id,
            provider=action.provider,
            operation=action.operation,
            status=execution.status,
            attempts=execution.attempts,
            external_id=execution.external_id,
            result=execution.result,
            last_error=execution.last_error,
            verification=(
                VerificationRead(
                    status=verification.status,
                    evidence=verification.evidence,
                    checked_at=verification.checked_at,
                )
                if verification
                else None
            ),
            created_at=execution.created_at,
            completed_at=execution.completed_at,
        )
        for execution, action, verification in rows
    ]


@router.post(
    "/{mission_id}/retry",
    status_code=status.HTTP_202_ACCEPTED,
    responses=ERRORS,
    summary="Retry failed or partially completed actions",
)
async def retry_execution(
    mission_id: uuid.UUID,
    identity: Operator,
    session: AsyncSession = Depends(get_session),
) -> dict[str, str]:
    mission = (
        await session.execute(
            select(Mission)
            .where(Mission.id == mission_id, Mission.workspace_id == identity.workspace.id)
            .with_for_update()
        )
    ).scalar_one_or_none()
    if mission is None:
        raise HTTPException(status_code=404, detail="Mission not found")
    if mission.status not in {
        MissionStatus.FAILED,
        MissionStatus.PARTIALLY_COMPLETE,
        MissionStatus.BLOCKED,
    }:
        raise HTTPException(status_code=409, detail="Mission is not retryable")
    executions = list(
        await session.scalars(
            select(ExecutionRecord).where(
                ExecutionRecord.mission_id == mission.id,
                ExecutionRecord.status == "failed",
            )
        )
    )
    if not executions:
        raise HTTPException(status_code=409, detail="No failed actions to retry")
    for execution in executions:
        execution.status = "pending"
        execution.last_error = None
        execution.attempts = 0
    transition_mission(
        session, mission, MissionStatus.RUNNING, "Execution retry requested", identity.user.id
    )
    session.add(
        OutboxJob(
            workspace_id=mission.workspace_id,
            mission_id=mission.id,
            job_type="execute_mission",
            payload={"retry": True},
            status="pending",
        )
    )
    record_mission_event(
        session,
        mission,
        "execution.retry_requested",
        "Execution retry requested",
        f"Retrying {len(executions)} failed action(s)",
        identity.user.id,
    )
    await session.commit()
    return {"status": "queued", "mission_id": str(mission.id)}
