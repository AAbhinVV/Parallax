import json
import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from parallax_backend.config import settings
from parallax_backend.database import get_session
from parallax_backend.dependencies import RequestIdentity, get_current_identity
from parallax_backend.models import (
    ActionProposal,
    ApprovalBundle,
    AuditEvent,
    ExecutionRecord,
    Integration,
    IntegrationProvider,
    KnowledgeFact,
    Mission,
    MissionStatus,
    MissionTransition,
    VerificationRecord,
)
from parallax_backend.schemas import (
    AnalyticsOverviewRead,
    AuditEventRead,
    ErrorResponse,
    IntegrationHealthRead,
    MissionSLARead,
    ProviderExecutionRead,
    StatusCountRead,
    TimelineEventRead,
)

router = APIRouter(prefix="/api", tags=["analytics"])
ERRORS: dict[int | str, dict[str, Any]] = {
    401: {"model": ErrorResponse},
    403: {"model": ErrorResponse},
    404: {"model": ErrorResponse},
}
DISPLAY = {
    IntegrationProvider.GITHUB: "GitHub",
    IntegrationProvider.JIRA: "Jira",
    IntegrationProvider.NOTION: "Notion",
    IntegrationProvider.SLACK: "Slack",
}


async def _mission(
    session: AsyncSession, workspace_id: uuid.UUID, mission_id: uuid.UUID
) -> Mission:
    mission = await session.scalar(
        select(Mission).where(Mission.id == mission_id, Mission.workspace_id == workspace_id)
    )
    if mission is None:
        raise HTTPException(status_code=404, detail="Mission not found")
    return mission


def _compact_detail(value: Any, limit: int = 300) -> str:
    return json.dumps(value, sort_keys=True, default=str)[:limit]


# Deterministic tiebreak for events sharing a timestamp: transitions are
# the macro steps, the other event types are the details within them.
_EVENT_ORDER = {
    "mission.transition": 0,
    "approval.bundle": 1,
    "knowledge.fact": 2,
    "execution": 3,
    "verification": 4,
}

# Within tied transitions, order by lifecycle position (databases with
# second-precision timestamps cannot distinguish them otherwise).
_TRANSITION_RANK = {
    MissionStatus.QUEUED: 0,
    MissionStatus.PLANNING: 1,
    MissionStatus.CONTEXT_COLLECTED: 2,
    MissionStatus.WAITING_FOR_APPROVAL: 3,
    MissionStatus.RUNNING: 4,
    MissionStatus.PARTIALLY_COMPLETE: 5,
    MissionStatus.BLOCKED: 5,
    MissionStatus.COMPLETED: 6,
    MissionStatus.REJECTED: 6,
    MissionStatus.CANCELLED: 6,
    MissionStatus.FAILED: 6,
}


@router.get(
    "/missions/{mission_id}/timeline",
    response_model=list[TimelineEventRead],
    responses=ERRORS,
    summary="Get the complete mission timeline",
)
async def mission_timeline(
    mission_id: uuid.UUID,
    identity: RequestIdentity = Depends(get_current_identity),
    session: AsyncSession = Depends(get_session),
) -> list[TimelineEventRead]:
    """Merged, chronological mission timeline.

    Every durable trace of what happened inside one mission, in order:
    status transitions, knowledge-base facts, action executions,
    verifications, and approval decisions.
    """
    await _mission(session, identity.workspace.id, mission_id)
    events: list[tuple[datetime, int, int, str, TimelineEventRead]] = []

    transitions = list(
        await session.scalars(
            select(MissionTransition)
            .where(
                MissionTransition.workspace_id == identity.workspace.id,
                MissionTransition.mission_id == mission_id,
            )
            .order_by(MissionTransition.created_at, MissionTransition.id)
        )
    )
    for item in transitions:
        events.append(
            (
                item.created_at,
                _EVENT_ORDER["mission.transition"],
                _TRANSITION_RANK[item.to_status],
                str(item.id),
                TimelineEventRead(
                    id=item.id,
                    event_type="mission.transition",
                    from_status=item.from_status,
                    to_status=item.to_status,
                    title=f"Mission {item.to_status.value}",
                    detail=item.reason,
                    actor_user_id=item.actor_user_id,
                    created_at=item.created_at,
                ),
            )
        )

    facts = list(
        await session.scalars(
            select(KnowledgeFact).where(
                KnowledgeFact.workspace_id == identity.workspace.id,
                KnowledgeFact.mission_id == mission_id,
            )
        )
    )
    for fact in facts:
        events.append(
            (
                fact.observed_at,
                _EVENT_ORDER["knowledge.fact"],
                0,
                str(fact.id),
                TimelineEventRead(
                    id=fact.id,
                    event_type="knowledge.fact",
                    title=f"{fact.kind.value} · {fact.source.value}:{fact.source_ref}",
                    detail=fact.fact,
                    created_at=fact.observed_at,
                ),
            )
        )

    execution_rows = (
        await session.execute(
            select(ExecutionRecord, ActionProposal)
            .join(ActionProposal, ActionProposal.id == ExecutionRecord.action_proposal_id)
            .where(
                ExecutionRecord.workspace_id == identity.workspace.id,
                ExecutionRecord.mission_id == mission_id,
            )
        )
    ).all()
    for execution, action in execution_rows:
        detail = f"{execution.status} (attempts: {execution.attempts})"
        if execution.external_id:
            detail = f"{detail} → {execution.external_id}"
        if execution.last_error:
            detail = f"{detail} — {execution.last_error[:200]}"
        events.append(
            (
                execution.created_at,
                _EVENT_ORDER["execution"],
                0,
                str(execution.id),
                TimelineEventRead(
                    id=execution.id,
                    event_type="execution",
                    title=f"{action.provider.value} {action.operation}",
                    detail=detail,
                    created_at=execution.created_at,
                ),
            )
        )

    verifications = list(
        await session.scalars(
            select(VerificationRecord).where(
                VerificationRecord.workspace_id == identity.workspace.id,
                VerificationRecord.mission_id == mission_id,
            )
        )
    )
    for verification in verifications:
        events.append(
            (
                verification.checked_at,
                _EVENT_ORDER["verification"],
                0,
                str(verification.id),
                TimelineEventRead(
                    id=verification.id,
                    event_type="verification",
                    title=f"Verification {verification.status}",
                    detail=_compact_detail(verification.evidence),
                    created_at=verification.checked_at,
                ),
            )
        )

    bundles = list(
        await session.scalars(
            select(ApprovalBundle).where(
                ApprovalBundle.workspace_id == identity.workspace.id,
                ApprovalBundle.mission_id == mission_id,
            )
        )
    )
    for bundle in bundles:
        created_at = bundle.decided_at or bundle.created_at
        events.append(
            (
                created_at,
                _EVENT_ORDER["approval.bundle"],
                0,
                str(bundle.id),
                TimelineEventRead(
                    id=bundle.id,
                    event_type="approval.bundle",
                    title=f"Approval bundle {bundle.status}",
                    detail=bundle.decision_note or f"Bundle v{bundle.version} is {bundle.status}",
                    actor_user_id=bundle.decided_by_user_id,
                    created_at=created_at,
                ),
            )
        )

    events.sort(key=lambda item: (item[0], item[1], item[2], item[3]))
    return [event for _, _, _, _, event in events]


@router.get(
    "/audit-events",
    response_model=list[AuditEventRead],
    responses=ERRORS,
    summary="List immutable workspace audit events",
)
async def audit_events(
    identity: RequestIdentity = Depends(get_current_identity),
    session: AsyncSession = Depends(get_session),
    mission_id: uuid.UUID | None = None,
    event_type: str | None = Query(default=None, max_length=120),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[AuditEventRead]:
    statement = select(AuditEvent).where(AuditEvent.workspace_id == identity.workspace.id)
    if mission_id is not None:
        statement = statement.where(AuditEvent.mission_id == mission_id)
    if event_type is not None:
        statement = statement.where(AuditEvent.event_type == event_type)
    records = list(
        await session.scalars(
            statement.order_by(AuditEvent.created_at.desc(), AuditEvent.id.desc())
            .offset(offset)
            .limit(limit)
        )
    )
    return [
        AuditEventRead(
            id=item.id,
            mission_id=item.mission_id,
            actor_user_id=item.actor_user_id,
            event_type=item.event_type,
            correlation_id=item.correlation_id,
            payload=item.payload,
            created_at=item.created_at,
        )
        for item in records
    ]


@router.get(
    "/missions/{mission_id}/sla",
    response_model=MissionSLARead,
    responses=ERRORS,
    summary="Get mission SLA state",
)
async def mission_sla(
    mission_id: uuid.UUID,
    identity: RequestIdentity = Depends(get_current_identity),
    session: AsyncSession = Depends(get_session),
) -> MissionSLARead:
    mission = await _mission(session, identity.workspace.id, mission_id)
    created_at = mission.created_at
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=UTC)
    age = max(0, int((datetime.now(UTC) - created_at).total_seconds()))
    target = settings.mission_sla_minutes * 60
    terminal = mission.status in {
        MissionStatus.COMPLETED,
        MissionStatus.REJECTED,
        MissionStatus.CANCELLED,
    }
    return MissionSLARead(
        mission_id=mission.id,
        status=mission.status,
        age_seconds=age,
        target_seconds=target,
        remaining_seconds=max(0, target - age),
        breached=not terminal and age > target,
    )


@router.get(
    "/analytics/overview",
    response_model=AnalyticsOverviewRead,
    responses=ERRORS,
    summary="Get workspace mission and execution analytics",
)
async def analytics_overview(
    identity: RequestIdentity = Depends(get_current_identity),
    session: AsyncSession = Depends(get_session),
) -> AnalyticsOverviewRead:
    status_rows = (
        await session.execute(
            select(Mission.status, func.count(Mission.id))
            .where(Mission.workspace_id == identity.workspace.id)
            .group_by(Mission.status)
        )
    ).all()
    counts = {status: int(count) for status, count in status_rows}
    total = sum(counts.values())
    completed = counts.get(MissionStatus.COMPLETED, 0)
    execution_rows = (
        await session.execute(
            select(ExecutionRecord.status, func.count(ExecutionRecord.id))
            .where(ExecutionRecord.workspace_id == identity.workspace.id)
            .group_by(ExecutionRecord.status)
        )
    ).all()
    execution_counts = {status: int(count) for status, count in execution_rows}
    execution_total = sum(execution_counts.values())
    provider_rows = (
        await session.execute(
            select(ActionProposal.provider, ExecutionRecord.status, func.count(ExecutionRecord.id))
            .join(ActionProposal, ActionProposal.id == ExecutionRecord.action_proposal_id)
            .where(ExecutionRecord.workspace_id == identity.workspace.id)
            .group_by(ActionProposal.provider, ExecutionRecord.status)
        )
    ).all()
    by_provider: dict[IntegrationProvider, dict[str, int]] = {}
    for provider, status, count in provider_rows:
        by_provider.setdefault(provider, {})[status] = int(count)
    completion_times = (
        await session.execute(
            select(Mission.created_at, Mission.updated_at).where(
                Mission.workspace_id == identity.workspace.id,
                Mission.status == MissionStatus.COMPLETED,
            )
        )
    ).all()
    durations = [(updated - created).total_seconds() for created, updated in completion_times]
    completed_duration = sum(durations) / len(durations) if durations else None
    return AnalyticsOverviewRead(
        total_missions=total,
        completion_rate_pct=round((completed / total * 100) if total else 0.0, 2),
        verification_rate_pct=round(
            (execution_counts.get("verified", 0) / execution_total * 100)
            if execution_total
            else 0.0,
            2,
        ),
        average_completion_seconds=(
            round(float(completed_duration), 2) if completed_duration else None
        ),
        missions_by_status=[
            StatusCountRead(status=status, count=counts.get(status, 0)) for status in MissionStatus
        ],
        executions_by_provider=[
            ProviderExecutionRead(
                provider=provider,
                verified=by_provider.get(provider, {}).get("verified", 0),
                failed=by_provider.get(provider, {}).get("failed", 0),
            )
            for provider in IntegrationProvider
        ],
    )


@router.get(
    "/integrations/health",
    response_model=list[IntegrationHealthRead],
    responses=ERRORS,
    summary="Get stored health for all four integrations",
)
async def integration_health(
    identity: RequestIdentity = Depends(get_current_identity),
    session: AsyncSession = Depends(get_session),
) -> list[IntegrationHealthRead]:
    records = list(
        await session.scalars(
            select(Integration).where(Integration.workspace_id == identity.workspace.id)
        )
    )
    by_provider = {item.provider: item for item in records}
    return [
        IntegrationHealthRead(
            name=DISPLAY[provider],
            status=(record.status.value if (record := by_provider.get(provider)) else "missing"),
            mode=settings.integration_mode,
            last_checked_at=record.last_checked_at if record else None,
            detail=(record.configuration.get("last_message") if record else None)
            or "Connection has not been checked",
        )
        for provider in IntegrationProvider
    ]
