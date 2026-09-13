from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.dependencies import RequestIdentity, get_current_identity
from app.models import ActivityRecord, Mission, MissionStatus, Project
from app.schemas import ActivityRead, DashboardStatsRead, ErrorResponse, ProjectRead

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])
ERRORS: dict[int | str, dict[str, Any]] = {
    401: {"model": ErrorResponse},
    403: {"model": ErrorResponse},
}


@router.get(
    "/stats", response_model=DashboardStatsRead, responses=ERRORS, summary="Dashboard stats"
)
async def stats(
    identity: RequestIdentity = Depends(get_current_identity),
    session: AsyncSession = Depends(get_session),
) -> DashboardStatsRead:
    rows = (
        await session.execute(
            select(Mission.status, func.count(Mission.id))
            .where(Mission.workspace_id == identity.workspace.id)
            .group_by(Mission.status)
        )
    ).all()
    counts: dict[MissionStatus, int] = {row[0]: int(row[1]) for row in rows}
    completed_week = int(
        await session.scalar(
            select(func.count(Mission.id)).where(
                Mission.workspace_id == identity.workspace.id,
                Mission.status == MissionStatus.COMPLETED,
                Mission.updated_at >= datetime.now(UTC) - timedelta(days=7),
            )
        )
        or 0
    )
    health = int(
        round(
            float(
                await session.scalar(
                    select(func.avg(Project.health_pct)).where(
                        Project.workspace_id == identity.workspace.id
                    )
                )
                or 0
            )
        )
    )
    active = sum(
        counts.get(item, 0)
        for item in (
            MissionStatus.QUEUED,
            MissionStatus.PLANNING,
            MissionStatus.CONTEXT_COLLECTED,
            MissionStatus.RUNNING,
        )
    )
    return DashboardStatsRead(
        active_tasks=active,
        completed_this_week=completed_week,
        blocked=counts.get(MissionStatus.BLOCKED, 0) + counts.get(MissionStatus.FAILED, 0),
        awaiting_approval=counts.get(MissionStatus.WAITING_FOR_APPROVAL, 0),
        project_health_pct=health,
    )


@router.get(
    "/activity", response_model=list[ActivityRead], responses=ERRORS, summary="Recent activity"
)
async def activity(
    identity: RequestIdentity = Depends(get_current_identity),
    session: AsyncSession = Depends(get_session),
    limit: int = Query(default=10, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> list[ActivityRead]:
    records = (
        await session.execute(
            select(ActivityRecord)
            .where(ActivityRecord.workspace_id == identity.workspace.id)
            .order_by(ActivityRecord.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
    ).scalars()
    return [
        ActivityRead(
            id=record.id,
            mission_id=record.mission_id,
            icon=record.icon,
            title=record.title,
            detail=record.detail,
            created_at=record.created_at,
        )
        for record in records
    ]


@router.get("/projects", response_model=list[ProjectRead], responses=ERRORS, summary="Projects")
async def projects(
    identity: RequestIdentity = Depends(get_current_identity),
    session: AsyncSession = Depends(get_session),
) -> list[ProjectRead]:
    records = (
        await session.execute(
            select(Project)
            .where(Project.workspace_id == identity.workspace.id)
            .order_by(Project.name)
        )
    ).scalars()
    return [
        ProjectRead(id=item.id, name=item.name, icon=item.icon, health_pct=item.health_pct)
        for item in records
    ]
