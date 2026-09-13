import hashlib
import json
import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_session
from app.dependencies import RequestIdentity, get_current_identity, require_roles
from app.models import (
    AgentAssessment,
    AgentRun,
    ContextPack,
    IdempotencyRecord,
    Mission,
    MissionStatus,
    MissionTransition,
    OutboxJob,
    Project,
    WorkspaceRole,
)
from app.schemas import (
    AgentAssessmentRead,
    AgentProposalRead,
    ContextPackRead,
    ErrorResponse,
    EvidenceRead,
    MissionCreate,
    MissionRead,
    ReviewerCandidateRead,
)
from app.services.missions import mission_to_read, record_mission_event, transition_mission

router = APIRouter(prefix="/api/missions", tags=["missions"])
ERRORS: dict[int | str, dict[str, Any]] = {
    401: {"model": ErrorResponse},
    403: {"model": ErrorResponse},
    404: {"model": ErrorResponse},
    409: {"model": ErrorResponse},
    422: {"description": "Request validation failed"},
}
MissionCreator = Annotated[
    RequestIdentity,
    Depends(require_roles(WorkspaceRole.OWNER, WorkspaceRole.ADMIN, WorkspaceRole.MANAGER)),
]


async def load_mission(
    session: AsyncSession, workspace_id: uuid.UUID, mission_id: uuid.UUID, *, lock: bool = False
) -> Mission:
    statement = (
        select(Mission)
        .options(selectinload(Mission.steps))
        .where(Mission.id == mission_id, Mission.workspace_id == workspace_id)
    )
    if lock:
        statement = statement.with_for_update()
    mission = (await session.execute(statement)).scalar_one_or_none()
    if mission is None:
        raise HTTPException(status_code=404, detail="Mission not found")
    return mission


@router.post(
    "",
    response_model=MissionRead,
    status_code=status.HTTP_202_ACCEPTED,
    responses=ERRORS,
    summary="Submit a manual mission",
)
async def create_mission(
    payload: MissionCreate,
    request: Request,
    identity: MissionCreator,
    session: AsyncSession = Depends(get_session),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key", max_length=128),
) -> MissionRead:
    """Persist a manual mission and its outbox job atomically; no agent runs inline."""
    request_hash = hashlib.sha256(
        json.dumps(payload.model_dump(), sort_keys=True).encode("utf-8")
    ).hexdigest()
    if idempotency_key:
        existing = (
            await session.execute(
                select(IdempotencyRecord).where(
                    IdempotencyRecord.workspace_id == identity.workspace.id,
                    IdempotencyRecord.key == idempotency_key,
                )
            )
        ).scalar_one_or_none()
        if existing:
            if existing.request_hash != request_hash:
                raise HTTPException(
                    status_code=409, detail="Idempotency key was used for another request"
                )
            return mission_to_read(
                await load_mission(session, identity.workspace.id, existing.resource_id)
            )

    project = (
        await session.execute(
            select(Project).where(
                Project.workspace_id == identity.workspace.id,
                Project.name == payload.project,
            )
        )
    ).scalar_one_or_none()
    if project is None:
        raise HTTPException(status_code=422, detail="Project is not available in this workspace")

    mission = Mission(
        workspace_id=identity.workspace.id,
        created_by_user_id=identity.user.id,
        project_id=project.id,
        prompt=payload.prompt,
        project_name=project.name,
        status=MissionStatus.QUEUED,
        progress_current=0,
        progress_total=1,
        correlation_id=request.state.correlation_id,
    )
    session.add(mission)
    await session.flush()
    session.add_all(
        [
            MissionTransition(
                workspace_id=identity.workspace.id,
                mission_id=mission.id,
                from_status=None,
                to_status=MissionStatus.QUEUED,
                reason="Manual mission submitted",
                actor_user_id=identity.user.id,
            ),
            OutboxJob(
                workspace_id=identity.workspace.id,
                mission_id=mission.id,
                job_type="prepare_mission",
                payload={"mission_id": str(mission.id)},
                status="pending",
            ),
        ]
    )
    record_mission_event(
        session,
        mission,
        "mission.created",
        "Mission queued",
        f"Mission submitted for {project.name}",
        identity.user.id,
    )
    if idempotency_key:
        session.add(
            IdempotencyRecord(
                workspace_id=identity.workspace.id,
                key=idempotency_key,
                request_hash=request_hash,
                resource_type="mission",
                resource_id=mission.id,
            )
        )
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(status_code=409, detail="Duplicate mission request") from None
    return mission_to_read(await load_mission(session, identity.workspace.id, mission.id))


@router.get("", response_model=list[MissionRead], responses=ERRORS, summary="List missions")
async def list_missions(
    identity: RequestIdentity = Depends(get_current_identity),
    session: AsyncSession = Depends(get_session),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> list[MissionRead]:
    missions = (
        await session.execute(
            select(Mission)
            .options(selectinload(Mission.steps))
            .where(Mission.workspace_id == identity.workspace.id)
            .order_by(Mission.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
    ).scalars()
    return [mission_to_read(mission) for mission in missions.unique().all()]


@router.get("/{mission_id}", response_model=MissionRead, responses=ERRORS, summary="Get a mission")
async def get_mission(
    mission_id: uuid.UUID,
    identity: RequestIdentity = Depends(get_current_identity),
    session: AsyncSession = Depends(get_session),
) -> MissionRead:
    return mission_to_read(await load_mission(session, identity.workspace.id, mission_id))


@router.get(
    "/{mission_id}/context-pack",
    response_model=ContextPackRead,
    responses=ERRORS,
    summary="Get a mission Context Pack",
)
async def get_context_pack(
    mission_id: uuid.UUID,
    identity: RequestIdentity = Depends(get_current_identity),
    session: AsyncSession = Depends(get_session),
) -> ContextPackRead:
    context_pack = (
        await session.execute(
            select(ContextPack)
            .options(selectinload(ContextPack.evidence))
            .where(
                ContextPack.mission_id == mission_id,
                ContextPack.workspace_id == identity.workspace.id,
            )
            .order_by(ContextPack.version.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    if context_pack is None:
        raise HTTPException(status_code=404, detail="Context Pack not found")
    return ContextPackRead(
        id=context_pack.id,
        mission_id=context_pack.mission_id,
        version=context_pack.version,
        summary=context_pack.summary,
        content=context_pack.content,
        content_hash=context_pack.content_hash,
        evidence=[
            EvidenceRead(
                key=item.key,
                provider=item.provider,
                external_id=item.external_id,
                title=item.title,
                url=item.url,
                excerpt=item.excerpt,
                created_at=item.created_at,
            )
            for item in context_pack.evidence
        ],
        created_at=context_pack.created_at,
    )


@router.get(
    "/{mission_id}/assessment",
    response_model=AgentAssessmentRead,
    responses=ERRORS,
    summary="Get a validated Agent assessment",
)
async def get_assessment(
    mission_id: uuid.UUID,
    identity: RequestIdentity = Depends(get_current_identity),
    session: AsyncSession = Depends(get_session),
) -> AgentAssessmentRead:
    row = (
        await session.execute(
            select(AgentAssessment, AgentRun)
            .join(AgentRun, AgentRun.id == AgentAssessment.agent_run_id)
            .where(
                AgentAssessment.mission_id == mission_id,
                AgentAssessment.workspace_id == identity.workspace.id,
            )
        )
    ).one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Agent assessment not found")
    assessment, run = row
    return AgentAssessmentRead(
        id=assessment.id,
        mission_id=assessment.mission_id,
        mode=run.mode,
        context_summary=assessment.context_summary,
        risk_level=assessment.risk_level,
        risk_factors=assessment.risk_factors,
        review_effort_minutes=assessment.review_effort_minutes,
        effort_rationale=assessment.effort_rationale,
        confidence=assessment.confidence,
        explanation=assessment.explanation,
        reviewer_candidates=[
            ReviewerCandidateRead.model_validate(item) for item in assessment.reviewer_candidates
        ],
        citations=assessment.citations,
        proposals=[AgentProposalRead.model_validate(item) for item in assessment.proposals],
        created_at=assessment.created_at,
    )


@router.post(
    "/{mission_id}/cancel",
    response_model=MissionRead,
    responses=ERRORS,
    summary="Cancel a mission",
)
async def cancel_mission(
    mission_id: uuid.UUID,
    identity: MissionCreator,
    session: AsyncSession = Depends(get_session),
) -> MissionRead:
    mission = await load_mission(session, identity.workspace.id, mission_id, lock=True)
    transition_mission(
        session, mission, MissionStatus.CANCELLED, "Cancelled by user", identity.user.id
    )
    pending_jobs = (
        await session.execute(
            select(OutboxJob).where(
                OutboxJob.mission_id == mission.id,
                OutboxJob.workspace_id == identity.workspace.id,
                OutboxJob.status == "pending",
            )
        )
    ).scalars()
    for job in pending_jobs:
        job.status = "cancelled"
    record_mission_event(
        session,
        mission,
        "mission.cancelled",
        "Mission cancelled",
        "Cancelled before completion",
        identity.user.id,
    )
    await session.commit()
    return mission_to_read(await load_mission(session, identity.workspace.id, mission.id))
