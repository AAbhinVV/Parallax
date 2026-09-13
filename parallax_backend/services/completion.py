"""K3.2 completion proofs: durable evidence that a mission really finished.

The proof is the database's answer to "did this operational objective
actually complete?" — assembled from verified execution records, not from
what the agent claims. No verified execution -> no proof.
"""

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    ActionProposal,
    ExecutionRecord,
    Mission,
    MissionCompletionProof,
    VerificationRecord,
)


async def build_completion_proof(
    session: AsyncSession,
    mission: Mission,
) -> MissionCompletionProof | None:
    """Assemble the verified completion proof for a mission.

    Returns None when no execution was verified: without verified
    completion there is nothing to prove. Called when a mission transitions
    to COMPLETED; safe to call again on re-completion (refreshes the proof
    in place instead of duplicating rows).
    """
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
    proposals = {
        proposal.id: proposal
        for proposal in (
            await session.execute(
                select(ActionProposal).where(ActionProposal.mission_id == mission.id)
            )
        )
        .scalars()
        .all()
    }
    verifications = {
        record.execution_id: record
        for record in (
            await session.execute(
                select(VerificationRecord).where(VerificationRecord.mission_id == mission.id)
            )
        )
        .scalars()
        .all()
    }

    verified_actions: list[dict[str, Any]] = []
    verification_ids: list[str] = []
    for proposal_id, execution in executions.items():
        if execution.status != "verified":
            continue
        proposal = proposals.get(proposal_id)
        verification = verifications.get(execution.id)
        verified_actions.append(
            {
                "provider": proposal.provider.value if proposal else "unknown",
                "operation": proposal.operation if proposal else "unknown",
                "external_id": execution.external_id,
                "verified": True,
                "verification_id": str(verification.id) if verification else None,
            }
        )
        if verification is not None:
            verification_ids.append(str(verification.id))

    if not verified_actions:
        return None

    completed_at = datetime.now(UTC)
    existing = (
        await session.execute(
            select(MissionCompletionProof).where(MissionCompletionProof.mission_id == mission.id)
        )
    ).scalar_one_or_none()
    if existing is not None:
        existing.status = "verified"
        existing.actions = verified_actions
        existing.verification_ids = verification_ids
        existing.completed_at = completed_at
        return existing

    proof = MissionCompletionProof(
        workspace_id=mission.workspace_id,
        mission_id=mission.id,
        status="verified",
        actions=verified_actions,
        verification_ids=verification_ids,
        completed_at=completed_at,
    )
    session.add(proof)
    await session.flush()
    return proof


async def verified_proof_for(
    session: AsyncSession,
    mission_id: uuid.UUID,
) -> MissionCompletionProof | None:
    """The verified proof for a mission, or None (missing/legacy proof)."""
    return (
        await session.execute(
            select(MissionCompletionProof).where(MissionCompletionProof.mission_id == mission_id)
        )
    ).scalar_one_or_none()
