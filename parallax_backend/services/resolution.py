"""K3.3 duplicate/resume resolution: create, resume, or recognize existing work.

The database decides — not the agent — whether a previous mission already
fulfilled the same operational objective:

    new task
      -> fingerprint lookup over previous missions
      -> same completed operational objective with a verified proof?
           yes -> report already completed (no duplicate execution)
           no  -> create/resume normally

A mission that completed without a verified proof is treated as
resumable, never as done: memory without evidence is not truth.
"""

import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from parallax_backend.models import Mission, MissionCompletionProof, MissionStatus
from parallax_backend.services.completion import verified_proof_for
from parallax_backend.services.task_identity import task_fingerprint

_TERMINAL_NON_COMPLETED = (MissionStatus.CANCELLED, MissionStatus.REJECTED)


@dataclass(frozen=True)
class ObjectiveResolution:
    decision: str  # "new" | "resume" | "completed"
    fingerprint: str
    prior_mission: Mission | None
    proof: MissionCompletionProof | None


async def resolve_existing_objective(
    session: AsyncSession,
    workspace_id: uuid.UUID,
    project_id: uuid.UUID,
    prompt: str,
) -> ObjectiveResolution:
    """Resolve a task prompt against previous missions in the same project.

    The lookup is scoped to one workspace and one project: the same prompt
    in a different project is a different operational objective.
    """
    fingerprint = task_fingerprint(prompt)
    prior = (
        (
            await session.execute(
                select(Mission)
                .options(selectinload(Mission.steps))
                .where(
                    Mission.workspace_id == workspace_id,
                    Mission.project_id == project_id,
                    Mission.task_fingerprint == fingerprint,
                )
                .order_by(Mission.created_at.desc())
                .limit(1)
            )
        )
        .scalars()
        .first()
    )

    if prior is None or prior.status in _TERMINAL_NON_COMPLETED:
        return ObjectiveResolution("new", fingerprint, None, None)

    if prior.status is MissionStatus.COMPLETED:
        proof = await verified_proof_for(session, prior.id)
        if proof is not None and proof.status == "verified":
            return ObjectiveResolution("completed", fingerprint, prior, proof)
        return ObjectiveResolution("resume", fingerprint, prior, None)

    return ObjectiveResolution("resume", fingerprint, prior, None)
