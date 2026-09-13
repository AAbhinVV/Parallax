"""K4.1 durable mission runtime: deterministic step execution control.

The runtime is non-LLM. It owns worker leases, step state, retry
classification, crash recovery and resume ordering; the agent owns
reasoning and planning.

A worker claims a mission by taking a DB-persisted lease. The worker
renews the lease while it works. If the worker disappears, the lease
expires and another worker can reclaim the mission and continue from the
persisted safe point — verified actions are never re-executed.

State machine (per action, mirrored onto MissionStep):

    PENDING -> RUNNING -> VERIFIED
                      \\-> FAILED -> (retry under MAX_ATTEMPTS) -> RUNNING

The worker never infers progress from memory; it reads persisted state
(ExecutionRecord / MissionStep) every time.
"""

import uuid
from datetime import UTC, datetime, timedelta

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.integrations.contracts import AdapterError
from app.models import (
    ActionProposal,
    ApprovalBundle,
    ExecutionRecord,
    Mission,
    MissionStatus,
    MissionStep,
)
from app.services.missions import record_mission_event

LEASE_TTL_SECONDS = 60
MAX_ATTEMPTS = 3

# Workflow steps use sequences 1-3; action steps start after them.
_STEP_SEQUENCE_BASE = 10


def _as_aware(value: datetime) -> datetime:
    """Normalize a DB-loaded datetime to UTC-aware.

    SQLite stores naive wall-clock values; PostgreSQL returns aware ones.
    """
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


def is_retryable_error(exc: BaseException) -> bool:
    """Classify whether a failed action may be retried.

    Retryable: timeouts, connection errors, 429, temporary 5xx, and any
    AdapterError flagged retryable. Everything else (400/401/403, invalid
    actions, policy rejections) is not.
    """
    if isinstance(exc, AdapterError):
        return exc.retryable
    if isinstance(exc, (httpx.TimeoutException, httpx.ConnectError)):
        return True
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code in {429, 500, 502, 503, 504}
    return False


async def claim_mission(
    session: AsyncSession,
    mission_id: uuid.UUID,
    worker_id: str,
    *,
    lease_seconds: int = LEASE_TTL_SECONDS,
) -> bool:
    """Claim the execution lease on a mission.

    Claimable when no worker owns the lease or the previous lease expired.
    The caller owns the transaction.
    """
    mission = (
        await session.execute(select(Mission).where(Mission.id == mission_id).with_for_update())
    ).scalar_one_or_none()
    if mission is None:
        return False
    now = datetime.now(UTC)
    if (
        mission.worker_id is not None
        and mission.worker_id != worker_id
        and mission.lease_expires_at is not None
        and _as_aware(mission.lease_expires_at) > now
    ):
        return False
    mission.worker_id = worker_id
    mission.lease_expires_at = now + timedelta(seconds=lease_seconds)
    return True


async def renew_lease(
    session: AsyncSession,
    mission_id: uuid.UUID,
    worker_id: str,
    *,
    lease_seconds: int = LEASE_TTL_SECONDS,
) -> bool:
    """Extend the lease; only the owning worker may renew."""
    mission = (
        await session.execute(select(Mission).where(Mission.id == mission_id).with_for_update())
    ).scalar_one_or_none()
    if mission is None or mission.worker_id != worker_id:
        return False
    mission.lease_expires_at = datetime.now(UTC) + timedelta(seconds=lease_seconds)
    return True


async def release_lease(session: AsyncSession, mission_id: uuid.UUID, worker_id: str) -> None:
    """Release the lease when execution finishes (owned lease only)."""
    mission = (
        await session.execute(select(Mission).where(Mission.id == mission_id).with_for_update())
    ).scalar_one_or_none()
    if mission is None or mission.worker_id != worker_id:
        return
    mission.worker_id = None
    mission.lease_expires_at = None


async def recover_expired_missions(session: AsyncSession) -> list[uuid.UUID]:
    """Clear expired leases on RUNNING missions so workers can reclaim them.

    The mission stays RUNNING: it is still owned work. The caller requeues
    execute_mission for each returned id; the claiming worker resumes from
    the persisted safe point (verified actions are skipped).
    """
    now = datetime.now(UTC)
    missions = (
        (
            await session.execute(
                select(Mission)
                .where(
                    Mission.status == MissionStatus.RUNNING,
                    Mission.worker_id.is_not(None),
                    Mission.lease_expires_at.is_not(None),
                    Mission.lease_expires_at < now,
                )
                .with_for_update(skip_locked=True)
            )
        )
        .scalars()
        .all()
    )
    recovered: list[uuid.UUID] = []
    for mission in missions:
        previous_worker = mission.worker_id
        mission.worker_id = None
        mission.lease_expires_at = None
        record_mission_event(
            session,
            mission,
            "mission.worker_recovered",
            "Worker lease expired",
            f"Lease held by {previous_worker} expired; mission requeued for recovery",
            None,
        )
        recovered.append(mission.id)
    return recovered


async def get_runnable_actions(
    session: AsyncSession,
    mission: Mission,
) -> list[ActionProposal]:
    """Actions of the latest approved bundle that still need work.

    - verified executions are skipped (already done, evidence exists)
    - failed executions with attempts >= MAX_ATTEMPTS are excluded
      (max retries reached; an explicit /retry resets them)
    - everything else (no execution record, failed under the cap) runs
    """
    bundle = (
        await session.execute(
            select(ApprovalBundle)
            .options(selectinload(ApprovalBundle.actions))
            .where(
                ApprovalBundle.mission_id == mission.id,
                ApprovalBundle.status == "approved",
            )
            .order_by(ApprovalBundle.version.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    if bundle is None:
        return []
    executions = {
        record.action_proposal_id: record
        for record in (
            await session.execute(
                select(ExecutionRecord).where(ExecutionRecord.mission_id == mission.id)
            )
        )
        .scalars()
        .all()
    }
    runnable: list[ActionProposal] = []
    for action in bundle.actions:
        execution = executions.get(action.id)
        if execution is not None and execution.status == "verified":
            continue
        if execution is not None and execution.attempts >= MAX_ATTEMPTS:
            continue
        runnable.append(action)
    return runnable


async def upsert_action_step(
    session: AsyncSession,
    action: ActionProposal,
) -> MissionStep:
    """Find-or-create the durable step row for one action.

    Sequence = base + action.sequence keeps the mapping stable across
    worker restarts (the action sequence never changes).
    """
    sequence = _STEP_SEQUENCE_BASE + action.sequence
    step = (
        await session.execute(
            select(MissionStep).where(
                MissionStep.mission_id == action.mission_id, MissionStep.sequence == sequence
            )
        )
    ).scalar_one_or_none()
    if step is None:
        step = MissionStep(
            workspace_id=action.workspace_id,
            mission_id=action.mission_id,
            sequence=sequence,
            name=f"{action.provider.value}.{action.operation}",
            status="pending",
            detail="",
        )
        session.add(step)
        await session.flush()
    return step


def mark_step_started(step: MissionStep) -> None:
    step.status = "running"


def sync_step_from_execution(step: MissionStep, execution: ExecutionRecord) -> None:
    """Mirror the execution record's terminal state onto the step row.

    The execution record is the single source of truth for attempts and
    errors; the step row is the durable, inspectable projection.
    """
    step.status = execution.status
    step.attempts = execution.attempts
    step.last_error = execution.last_error
