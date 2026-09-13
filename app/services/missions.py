import uuid

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    ActivityRecord,
    AuditEvent,
    Mission,
    MissionStatus,
    MissionTransition,
)
from app.schemas import MissionRead, MissionStepRead

LEGAL_TRANSITIONS: dict[MissionStatus, frozenset[MissionStatus]] = {
    MissionStatus.QUEUED: frozenset(
        {MissionStatus.PLANNING, MissionStatus.CANCELLED, MissionStatus.FAILED}
    ),
    MissionStatus.PLANNING: frozenset(
        {
            MissionStatus.CONTEXT_COLLECTED,
            MissionStatus.CANCELLED,
            MissionStatus.BLOCKED,
            MissionStatus.FAILED,
        }
    ),
    MissionStatus.CONTEXT_COLLECTED: frozenset(
        {
            MissionStatus.WAITING_FOR_APPROVAL,
            MissionStatus.CANCELLED,
            MissionStatus.BLOCKED,
            MissionStatus.FAILED,
        }
    ),
    MissionStatus.WAITING_FOR_APPROVAL: frozenset(
        {
            MissionStatus.RUNNING,
            MissionStatus.REJECTED,
            MissionStatus.CANCELLED,
            MissionStatus.FAILED,
        }
    ),
    MissionStatus.RUNNING: frozenset(
        {
            MissionStatus.COMPLETED,
            MissionStatus.PARTIALLY_COMPLETE,
            MissionStatus.WAITING_FOR_EVENT,
            MissionStatus.BLOCKED,
            MissionStatus.CANCELLED,
            MissionStatus.FAILED,
        }
    ),
    MissionStatus.WAITING_FOR_EVENT: frozenset(
        {MissionStatus.RUNNING, MissionStatus.CANCELLED, MissionStatus.FAILED}
    ),
    MissionStatus.PARTIALLY_COMPLETE: frozenset(
        {MissionStatus.RUNNING, MissionStatus.WAITING_FOR_EVENT}
    ),
    MissionStatus.COMPLETED: frozenset(),
    MissionStatus.BLOCKED: frozenset({MissionStatus.RUNNING}),
    MissionStatus.REJECTED: frozenset(),
    MissionStatus.CANCELLED: frozenset(),
    MissionStatus.FAILED: frozenset({MissionStatus.RUNNING}),
}


def transition_mission(
    session: AsyncSession,
    mission: Mission,
    target: MissionStatus,
    reason: str,
    actor_user_id: uuid.UUID | None,
) -> None:
    if target not in LEGAL_TRANSITIONS[mission.status]:
        raise HTTPException(
            status_code=409,
            detail=f"Mission cannot transition from {mission.status.value} to {target.value}",
        )
    previous = mission.status
    mission.status = target
    mission.version += 1
    session.add(
        MissionTransition(
            workspace_id=mission.workspace_id,
            mission_id=mission.id,
            from_status=previous,
            to_status=target,
            reason=reason,
            actor_user_id=actor_user_id,
        )
    )


def mission_to_read(mission: Mission) -> MissionRead:
    return MissionRead(
        id=mission.id,
        prompt=mission.prompt,
        project=mission.project_name,
        status=mission.status,
        progress_current=mission.progress_current,
        progress_total=mission.progress_total,
        result_summary=mission.result_summary,
        steps=[
            MissionStepRead(
                id=step.id,
                sequence=step.sequence,
                name=step.name,
                status=step.status,
                detail=step.detail,
                created_at=step.created_at,
            )
            for step in mission.steps
        ],
        created_at=mission.created_at,
        updated_at=mission.updated_at,
    )


def record_mission_event(
    session: AsyncSession,
    mission: Mission,
    event_type: str,
    title: str,
    detail: str,
    actor_user_id: uuid.UUID | None,
) -> None:
    session.add_all(
        [
            ActivityRecord(
                workspace_id=mission.workspace_id,
                mission_id=mission.id,
                icon="mission",
                title=title,
                detail=detail,
            ),
            AuditEvent(
                workspace_id=mission.workspace_id,
                actor_user_id=actor_user_id,
                mission_id=mission.id,
                event_type=event_type,
                correlation_id=mission.correlation_id,
                payload={"status": mission.status.value},
            ),
        ]
    )
