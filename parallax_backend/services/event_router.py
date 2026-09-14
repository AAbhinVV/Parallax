"""K4.4 event router: external events wake affected missions.

This is the Apteva-style continuous-runtime seam:

    webhook event
      -> normalize
      -> deduplicate (replayed events never route twice)
      -> identify affected missions (KB facts referencing the entity)
      -> wake: WAITING_FOR_EVENT -> RUNNING
      -> enqueue execute_mission

The router never executes anything itself; it only requeues the existing
durable execution path, which re-reads persisted state, skips verified
actions, and asks for approval where policy requires it.
"""

import hashlib
import json
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from parallax_backend.models import AuditEvent, KnowledgeFact, Mission, MissionStatus, OutboxJob
from parallax_backend.services.missions import transition_mission

# Only events for these providers can wake missions; GitHub PR events are
# read-only signals, the rest are state changes on mission entities.
WAKEABLE_PROVIDERS = {"github", "jira", "slack", "notion"}

# How long a processed event identity stays deduplicated.
EVENT_DEDUPE_TTL = timedelta(hours=24)


def event_identity(
    provider: str, event_type: str, external_id: str | None, payload: dict[str, Any]
) -> str:
    """Stable identity for one external event occurrence.

    Replayed deliveries of the same event produce the same identity, so
    the router can ignore them (PRD: replayed events must not duplicate
    actions).
    """
    payload_hash = hashlib.sha256(
        json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
    ).hexdigest()[:16]
    return f"{provider}:{event_type}:{external_id or 'none'}:{payload_hash}"


async def _already_processed(session: AsyncSession, identity: str) -> bool:
    cutoff = datetime.now(UTC) - EVENT_DEDUPE_TTL
    existing = (
        await session.execute(
            select(AuditEvent.id).where(
                AuditEvent.event_type == f"webhook:{identity}",
                AuditEvent.created_at > cutoff,
            )
        )
    ).scalar_one_or_none()
    return existing is not None


async def route_event(
    session: AsyncSession,
    provider: str,
    event_type: str,
    external_id: str | None,
    payload: dict[str, Any] | None = None,
) -> list[uuid.UUID]:
    """Route one external event to affected missions.

    Returns the ids of missions that were woken (WAITING_FOR_EVENT ->
    RUNNING) or already RUNNING and requeued for a fresh execution pass.
    Deduplicated events return an empty list.
    """
    provider = provider.lower().strip()
    if provider not in WAKEABLE_PROVIDERS:
        return []

    payload = payload or {}
    identity = event_identity(provider, event_type, external_id, payload)
    if await _already_processed(session, identity):
        return []

    if external_id is None:
        return []

    # Find live missions whose knowledge base references this entity.
    mission_ids = (
        (
            await session.execute(
                select(KnowledgeFact.mission_id)
                .join(Mission, Mission.id == KnowledgeFact.mission_id)
                .where(
                    KnowledgeFact.source_ref == external_id,
                    Mission.status.in_(
                        [
                            MissionStatus.RUNNING,
                            MissionStatus.WAITING_FOR_EVENT,
                            MissionStatus.PARTIALLY_COMPLETE,
                        ]
                    ),
                )
                .distinct()
            )
        )
        .scalars()
        .all()
    )

    woken: list[uuid.UUID] = []
    workspace_id: uuid.UUID | None = None
    for mission_id in mission_ids:
        mission = (
            await session.execute(select(Mission).where(Mission.id == mission_id).with_for_update())
        ).scalar_one_or_none()
        if mission is None:
            continue
        if mission.status == MissionStatus.WAITING_FOR_EVENT:
            transition_mission(
                session,
                mission,
                MissionStatus.RUNNING,
                f"Woken by {provider} {event_type}",
                None,
            )
        elif mission.status == MissionStatus.RUNNING:
            continue  # already executing; the worker re-reads state anyway
        workspace_id = mission.workspace_id
        session.add(
            OutboxJob(
                workspace_id=mission.workspace_id,
                mission_id=mission.id,
                job_type="execute_mission",
                payload={"event": identity},
                status="pending",
            )
        )
        woken.append(mission.id)

    if workspace_id is not None:
        session.add(
            AuditEvent(
                workspace_id=workspace_id,
                actor_user_id=None,
                mission_id=woken[0] if woken else None,
                event_type=f"webhook:{identity}",
                correlation_id=uuid.uuid4(),
                payload={
                    "provider": provider,
                    "event_type": event_type,
                    "external_id": external_id,
                    "woken": [str(mission_id) for mission_id in woken],
                },
            )
        )
    return woken
