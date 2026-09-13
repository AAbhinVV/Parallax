import uuid
from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from parallax_backend.agent.contracts import AgentProposal
from parallax_backend.database import get_session
from parallax_backend.dependencies import RequestIdentity, require_roles
from parallax_backend.models import (
    ActionProposal,
    AgentAssessment,
    ApprovalBundle,
    AuditEvent,
    EvidenceItem,
    Mission,
    MissionStatus,
    OutboxJob,
    WorkspaceRole,
)
from parallax_backend.schemas import (
    ActionProposalInput,
    ActionProposalRead,
    ApprovalBundleRead,
    ApprovalDecisionRequest,
    ApprovalEditRequest,
    ErrorResponse,
    PolicyResultRead,
)
from parallax_backend.services.missions import record_mission_event, transition_mission
from parallax_backend.services.policy import evaluate_actions

router = APIRouter(tags=["approvals"])
ERRORS: dict[int | str, dict[str, Any]] = {
    401: {"model": ErrorResponse},
    403: {"model": ErrorResponse},
    404: {"model": ErrorResponse},
    409: {"model": ErrorResponse},
    422: {"description": "Request validation or policy evaluation failed"},
}
Approver = Annotated[
    RequestIdentity,
    Depends(require_roles(WorkspaceRole.OWNER, WorkspaceRole.ADMIN, WorkspaceRole.MANAGER)),
]


def bundle_read(bundle: ApprovalBundle) -> ApprovalBundleRead:
    return ApprovalBundleRead(
        id=bundle.id,
        mission_id=bundle.mission_id,
        version=bundle.version,
        status=bundle.status,
        policy=PolicyResultRead.model_validate(bundle.policy_result),
        actions=[
            ActionProposalRead(
                id=item.id,
                sequence=item.sequence,
                provider=item.provider,
                operation=item.operation,
                rationale=item.rationale,
                payload=item.payload,
                citations=item.citations,
                status=item.status,
            )
            for item in bundle.actions
        ],
        decided_by_user_id=bundle.decided_by_user_id,
        decided_at=bundle.decided_at,
        decision_note=bundle.decision_note,
        created_at=bundle.created_at,
    )


async def load_bundle(
    session: AsyncSession, workspace_id: uuid.UUID, bundle_id: uuid.UUID, *, lock: bool = False
) -> ApprovalBundle:
    query = (
        select(ApprovalBundle)
        .options(selectinload(ApprovalBundle.actions))
        .where(ApprovalBundle.id == bundle_id, ApprovalBundle.workspace_id == workspace_id)
    )
    if lock:
        query = query.with_for_update()
    bundle = (await session.execute(query)).scalar_one_or_none()
    if bundle is None:
        raise HTTPException(status_code=404, detail="Approval bundle not found")
    return bundle


async def evidence_keys(session: AsyncSession, mission_id: uuid.UUID) -> set[str]:
    return set(
        (
            await session.scalars(
                select(EvidenceItem.key)
                .join(EvidenceItem.context_pack)
                .where(EvidenceItem.context_pack.has(mission_id=mission_id))
            )
        ).all()
    )


async def create_bundle(
    session: AsyncSession,
    mission: Mission,
    assessment: AgentAssessment,
    inputs: list[ActionProposalInput],
    version: int,
) -> ApprovalBundle:
    typed = [AgentProposal.model_validate(item.model_dump()) for item in inputs]
    policy = evaluate_actions(
        typed, await evidence_keys(session, mission.id), assessment.confidence
    )
    if not policy.allowed:
        raise HTTPException(status_code=422, detail={"policy_reasons": policy.reasons})
    bundle = ApprovalBundle(
        workspace_id=mission.workspace_id,
        mission_id=mission.id,
        assessment_id=assessment.id,
        version=version,
        status="pending",
        policy_result=policy.as_dict(),
    )
    session.add(bundle)
    await session.flush()
    session.add_all(
        [
            ActionProposal(
                workspace_id=mission.workspace_id,
                mission_id=mission.id,
                approval_bundle_id=bundle.id,
                sequence=index,
                provider=item.provider,
                operation=item.operation,
                rationale=item.rationale,
                payload=item.payload,
                citations=item.citations,
                status="proposed",
            )
            for index, item in enumerate(inputs, start=1)
        ]
    )
    await session.flush()
    return await load_bundle(session, mission.workspace_id, bundle.id)


@router.post(
    "/api/missions/{mission_id}/approval",
    response_model=ApprovalBundleRead,
    status_code=status.HTTP_201_CREATED,
    responses=ERRORS,
    summary="Create a policy-checked approval bundle",
)
async def prepare_approval(
    mission_id: uuid.UUID,
    request: Request,
    identity: Approver,
    session: AsyncSession = Depends(get_session),
) -> ApprovalBundleRead:
    mission = (
        await session.execute(
            select(Mission)
            .where(Mission.id == mission_id, Mission.workspace_id == identity.workspace.id)
            .with_for_update()
        )
    ).scalar_one_or_none()
    if mission is None:
        raise HTTPException(status_code=404, detail="Mission not found")
    existing = (
        await session.execute(
            select(ApprovalBundle)
            .options(selectinload(ApprovalBundle.actions))
            .where(ApprovalBundle.mission_id == mission.id)
            .order_by(ApprovalBundle.version.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    if existing is not None:
        return bundle_read(existing)
    if mission.status != MissionStatus.CONTEXT_COLLECTED:
        raise HTTPException(status_code=409, detail="Mission context is not ready for approval")
    assessment = (
        await session.execute(
            select(AgentAssessment).where(AgentAssessment.mission_id == mission.id)
        )
    ).scalar_one()
    inputs = [ActionProposalInput.model_validate(item) for item in assessment.proposals]
    bundle = await create_bundle(session, mission, assessment, inputs, 1)
    transition_mission(
        session, mission, MissionStatus.WAITING_FOR_APPROVAL, "Policy checks passed", None
    )
    record_mission_event(
        session,
        mission,
        "approval.requested",
        "Approval requested",
        f"{len(inputs)} action(s) await a PM decision",
        identity.user.id,
    )
    session.add(
        AuditEvent(
            workspace_id=mission.workspace_id,
            actor_user_id=identity.user.id,
            mission_id=mission.id,
            event_type="policy.passed",
            correlation_id=request.state.correlation_id,
            payload=bundle.policy_result,
        )
    )
    await session.commit()
    return bundle_read(await load_bundle(session, mission.workspace_id, bundle.id))


@router.get(
    "/api/approvals/{bundle_id}",
    response_model=ApprovalBundleRead,
    responses=ERRORS,
    summary="Get an approval bundle",
)
async def get_approval(
    bundle_id: uuid.UUID,
    identity: Approver,
    session: AsyncSession = Depends(get_session),
) -> ApprovalBundleRead:
    return bundle_read(await load_bundle(session, identity.workspace.id, bundle_id))


async def decide(
    session: AsyncSession,
    identity: RequestIdentity,
    bundle: ApprovalBundle,
    target: MissionStatus,
    decision: str,
    note: str | None,
) -> ApprovalBundleRead:
    if bundle.status != "pending":
        raise HTTPException(status_code=409, detail="Approval bundle is no longer pending")
    mission = (
        await session.execute(
            select(Mission).where(Mission.id == bundle.mission_id).with_for_update()
        )
    ).scalar_one()
    bundle.status = decision
    bundle.decided_by_user_id = identity.user.id
    bundle.decided_at = datetime.now(UTC)
    bundle.decision_note = note
    for action in bundle.actions:
        action.status = decision
    if decision == "approved":
        transition_mission(
            session, mission, MissionStatus.RUNNING, "Actions approved", identity.user.id
        )
        session.add(
            OutboxJob(
                workspace_id=mission.workspace_id,
                mission_id=mission.id,
                job_type="execute_mission",
                payload={"approval_bundle_id": str(bundle.id)},
                status="pending",
            )
        )
    else:
        transition_mission(session, mission, target, f"Approval {decision}", identity.user.id)
    record_mission_event(
        session,
        mission,
        f"approval.{decision}",
        f"Approval {decision}",
        note or f"Approval bundle {decision}",
        identity.user.id,
    )
    await session.commit()
    return bundle_read(await load_bundle(session, identity.workspace.id, bundle.id))


@router.post(
    "/api/approvals/{bundle_id}/approve",
    response_model=ApprovalBundleRead,
    responses=ERRORS,
    summary="Approve actions",
)
async def approve(
    bundle_id: uuid.UUID,
    payload: ApprovalDecisionRequest,
    identity: Approver,
    session: AsyncSession = Depends(get_session),
) -> ApprovalBundleRead:
    return await decide(
        session,
        identity,
        await load_bundle(session, identity.workspace.id, bundle_id, lock=True),
        MissionStatus.RUNNING,
        "approved",
        payload.note,
    )


@router.post(
    "/api/approvals/{bundle_id}/reject",
    response_model=ApprovalBundleRead,
    responses=ERRORS,
    summary="Reject actions",
)
async def reject(
    bundle_id: uuid.UUID,
    payload: ApprovalDecisionRequest,
    identity: Approver,
    session: AsyncSession = Depends(get_session),
) -> ApprovalBundleRead:
    return await decide(
        session,
        identity,
        await load_bundle(session, identity.workspace.id, bundle_id, lock=True),
        MissionStatus.REJECTED,
        "rejected",
        payload.note,
    )


@router.post(
    "/api/approvals/{bundle_id}/cancel",
    response_model=ApprovalBundleRead,
    responses=ERRORS,
    summary="Cancel actions",
)
async def cancel(
    bundle_id: uuid.UUID,
    payload: ApprovalDecisionRequest,
    identity: Approver,
    session: AsyncSession = Depends(get_session),
) -> ApprovalBundleRead:
    return await decide(
        session,
        identity,
        await load_bundle(session, identity.workspace.id, bundle_id, lock=True),
        MissionStatus.CANCELLED,
        "cancelled",
        payload.note,
    )


@router.post(
    "/api/approvals/{bundle_id}/edit",
    response_model=ApprovalBundleRead,
    status_code=201,
    responses=ERRORS,
    summary="Edit and revalidate actions",
)
async def edit(
    bundle_id: uuid.UUID,
    payload: ApprovalEditRequest,
    identity: Approver,
    session: AsyncSession = Depends(get_session),
) -> ApprovalBundleRead:
    current = await load_bundle(session, identity.workspace.id, bundle_id, lock=True)
    if current.status != "pending":
        raise HTTPException(status_code=409, detail="Approval bundle is no longer pending")
    mission = await session.get(Mission, current.mission_id)
    assessment = await session.get(AgentAssessment, current.assessment_id)
    if mission is None or assessment is None:
        raise HTTPException(status_code=404, detail="Approval source not found")
    current.status = "revised"
    current.decided_by_user_id = identity.user.id
    current.decided_at = datetime.now(UTC)
    current.decision_note = payload.note
    revised = await create_bundle(
        session, mission, assessment, payload.actions, current.version + 1
    )
    await session.commit()
    return bundle_read(await load_bundle(session, identity.workspace.id, revised.id))
