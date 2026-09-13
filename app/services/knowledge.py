"""Mission knowledge base: append-only facts with provenance.

The knowledge base is the persistent operational memory of a mission.
It is append-only: facts are never updated in place and never deleted.
A new observation for the same subject (mission, kind, source, source_ref)
supersedes the previous live fact; contradictory observations can mark a
fact conflicted so the agent is warned instead of trusting stale memory.

Two knowledge kinds are strictly separated:

- ``source_fact``: what an integration actually returned (GitHub, Jira,
  Notion, Slack). This is observed knowledge.
- ``decision``: what the agent concluded. This is derived knowledge and is
  never treated as source truth.

The mission context pack built here is the bounded read-model the agent
receives on every call: current task, mission status summary, latest
verified facts (with fresh-vs-historical marking), recent actions with
execution outcomes, the latest approval state, recent mission
transitions, pending actions, and conflicts and recent decisions.
"""

from __future__ import annotations

import json
import re
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    ActionProposal,
    ApprovalBundle,
    ExecutionRecord,
    IntegrationProvider,
    KnowledgeFact,
    KnowledgeFactKind,
    KnowledgeFactStatus,
    KnowledgeSource,
    Mission,
    MissionTransition,
    VerificationRecord,
)

_LIVE_STATUSES = (KnowledgeFactStatus.OBSERVED, KnowledgeFactStatus.VERIFIED)

_MAX_CONTEXT_FACTS_PER_SOURCE = 6
_MAX_CONTEXT_DECISIONS = 5
_MAX_CONTEXT_ACTIONS = 5
_MAX_CONTEXT_CHARS = 12_000
_MAX_TRANSITIONS = 5
_PREVIOUS_SNIPPET_CHARS = 200
_ERROR_SNIPPET_CHARS = 200

# Entity references extracted from the task text. Facts about these
# entities always survive the per-source caps: the agent must never lose
# the thread of the exact objects the mission is about.
_ISSUE_KEY_PATTERN = re.compile(r"\b[A-Z][A-Z0-9]{1,9}-\d+\b")
_PR_PATTERN = re.compile(r"\bpr\s*#?(\d+)\b", re.IGNORECASE)
_CHANNEL_PATTERN = re.compile(r"(?<![\w#])#[A-Za-z0-9_-]{2,64}\b")

_SOURCE_BY_PROVIDER: dict[IntegrationProvider, KnowledgeSource] = {
    IntegrationProvider.GITHUB: KnowledgeSource.GITHUB,
    IntegrationProvider.JIRA: KnowledgeSource.JIRA,
    IntegrationProvider.NOTION: KnowledgeSource.NOTION,
    IntegrationProvider.SLACK: KnowledgeSource.SLACK,
}


def knowledge_source_for(provider: IntegrationProvider) -> KnowledgeSource:
    """Map an integration provider to its knowledge source."""
    return _SOURCE_BY_PROVIDER[provider]


def _utcnow() -> datetime:
    return datetime.now(UTC)


async def _live_subject_facts(
    session: AsyncSession,
    mission_id: uuid.UUID,
    *,
    kind: KnowledgeFactKind,
    source: KnowledgeSource,
    source_ref: str,
) -> list[KnowledgeFact]:
    """Latest-first list of live facts for one subject of a mission."""
    return list(
        (
            await session.execute(
                select(KnowledgeFact)
                .where(
                    KnowledgeFact.mission_id == mission_id,
                    KnowledgeFact.kind == kind,
                    KnowledgeFact.source == source,
                    KnowledgeFact.source_ref == source_ref,
                    KnowledgeFact.status.in_(_LIVE_STATUSES),
                )
                .order_by(KnowledgeFact.observed_at.desc(), KnowledgeFact.created_at.desc())
            )
        )
        .scalars()
        .all()
    )


async def record_fact(
    session: AsyncSession,
    mission: Mission,
    *,
    kind: KnowledgeFactKind,
    source: KnowledgeSource,
    source_ref: str,
    fact: str,
    data: dict[str, Any] | None = None,
    agent_run_id: uuid.UUID | None = None,
    confidence: float | None = None,
    verified: bool = False,
) -> KnowledgeFact:
    """Append a fact to the mission knowledge base.

    Append-only semantics:

    - Identical live fact for the same subject -> the existing fact is
      returned unchanged (idempotent, no duplicate rows).
    - Different value for the same subject -> previous live facts are
      marked ``superseded`` and linked to the new fact; the new fact
      becomes the only live one for that subject.

    The caller owns the transaction (``session.commit()``).
    """
    normalized_fact = fact.strip()
    live_facts = await _live_subject_facts(
        session,
        mission.id,
        kind=kind,
        source=source,
        source_ref=source_ref,
    )

    for existing in live_facts:
        if existing.fact.strip() == normalized_fact:
            return existing

    new_fact = KnowledgeFact(
        workspace_id=mission.workspace_id,
        mission_id=mission.id,
        kind=kind,
        source=source,
        source_ref=source_ref,
        fact=normalized_fact,
        data=data or {},
        status=KnowledgeFactStatus.VERIFIED if verified else KnowledgeFactStatus.OBSERVED,
        verified_at=_utcnow() if verified else None,
        agent_run_id=agent_run_id,
        confidence=confidence,
    )
    session.add(new_fact)
    await session.flush()  # assign new_fact.id for supersede links

    for stale in live_facts:
        stale.status = KnowledgeFactStatus.SUPERSEDED
        stale.superseded_by_id = new_fact.id

    return new_fact


def mark_fact_verified(
    session: AsyncSession,
    fact: KnowledgeFact,
) -> KnowledgeFact:
    """Promote an observed fact to verified (read-after-write confirmation)."""
    if fact.status is KnowledgeFactStatus.VERIFIED:
        return fact
    if fact.status not in (KnowledgeFactStatus.OBSERVED, KnowledgeFactStatus.CONFLICTED):
        raise ValueError(f"Fact {fact.id} in status {fact.status.value} cannot be verified")
    fact.status = KnowledgeFactStatus.VERIFIED
    fact.verified_at = _utcnow()
    return fact


def mark_fact_conflicted(
    session: AsyncSession,
    fact: KnowledgeFact,
    *,
    reason: str,
) -> KnowledgeFact:
    """Flag a fact as conflicted: fresh source data contradicts it."""
    fact.status = KnowledgeFactStatus.CONFLICTED
    fact.data = {**fact.data, "conflict_reason": reason}
    return fact


def _fact_payload(fact: KnowledgeFact) -> dict[str, Any]:
    return {
        "id": str(fact.id),
        "kind": fact.kind.value,
        "source": fact.source.value,
        "source_ref": fact.source_ref,
        "fact": fact.fact,
        "observed_at": fact.observed_at.isoformat(),
        "verified_at": fact.verified_at.isoformat() if fact.verified_at else None,
        "status": fact.status.value,
        "confidence": fact.confidence,
        "data": fact.data,
    }


def _snippet(text: str, limit: int) -> str:
    return text if len(text) <= limit else text[:limit]


def _extract_entity_refs(prompt: str) -> list[str]:
    """Deterministic entity references mentioned by the task text."""
    refs: set[str] = set(_ISSUE_KEY_PATTERN.findall(prompt))
    refs.update(f"PR-{number}" for number in _PR_PATTERN.findall(prompt))
    refs.update(_CHANNEL_PATTERN.findall(prompt))
    return sorted(refs)


def _fact_matches_entity(fact: KnowledgeFact, entity_refs: list[str]) -> bool:
    return any(ref == fact.source_ref or ref in fact.fact for ref in entity_refs)


def _serialized_size(pack: dict[str, Any]) -> int:
    return len(json.dumps(pack, sort_keys=True, default=str))


def _drop_last(pack: dict[str, Any], key: str) -> bool:
    """Drop the lowest-priority entry of a pack section.

    Protected entries (verified or entity-focused) are never dropped; the
    oldest non-protected entry goes first. Returns True when an entry was
    dropped, so budget enforcement can move to the next section.
    """
    items = pack.get(key)
    if not isinstance(items, list) or not items:
        return False
    for index in range(len(items) - 1, -1, -1):
        item = items[index]
        if isinstance(item, dict) and (
            item.get("status") == "verified" or item.get("entity_focus")
        ):
            continue
        items.pop(index)
        return True
    return False


def _enforce_budget(pack: dict[str, Any], budget: int) -> None:
    """Trim the pack to the character budget, lowest priority first.

    Guaranteed-alive sections (task, status summary, approval, pending
    work, conflicts, transitions) are never trimmed; the order of
    sacrifice is non-verified facts, then decisions, then recent actions.
    """
    while _serialized_size(pack) > budget:
        if _drop_last(pack, "facts"):
            continue
        if _drop_last(pack, "decisions"):
            continue
        if _drop_last(pack, "recent_actions"):
            continue
        break


async def build_mission_context(
    session: AsyncSession,
    mission: Mission,
    *,
    max_facts_per_source: int = _MAX_CONTEXT_FACTS_PER_SOURCE,
    max_decisions: int = _MAX_CONTEXT_DECISIONS,
    max_actions: int = _MAX_CONTEXT_ACTIONS,
    max_chars: int = _MAX_CONTEXT_CHARS,
) -> dict[str, Any]:
    """Assemble the bounded mission context pack for the next agent call.

    Contents (deterministically ordered, size-capped):

    - the current task, mission status and a mission status summary
      (completed work, remaining work, blockers) so the agent knows where
      the mission stands without replaying its whole history
    - latest live facts per source (verified first, then newest first;
      conflicts included) with fresh-vs-historical marking: the current
      fact per subject carries ``current`` and a capped ``previous`` line
      when an older observation was superseded, so drift is visible
    - facts about entities referenced in the task always survive the
      per-source caps (``entity_focus``)
    - recent decisions (derived knowledge, clearly separated)
    - recent and pending actions with execution attempts, external ids
      and errors
    - the latest approval state (decision, note, edit history) — the
      agent must know what the human decided
    - recent mission transitions (retries, approvals, cancellations)
    - open conflicts / uncertainties

    The pack is trimmed to ``max_chars`` by dropping the lowest-priority
    facts, decisions, and recent actions first. Keys are snake_case to
    match the backend agent contracts; adapters translate to agent-core
    payloads when bridging services.
    """
    entity_refs = _extract_entity_refs(mission.prompt)

    all_facts = list(
        (
            await session.execute(
                select(KnowledgeFact)
                .where(
                    KnowledgeFact.mission_id == mission.id,
                    KnowledgeFact.kind == KnowledgeFactKind.SOURCE_FACT,
                )
                .order_by(KnowledgeFact.observed_at.desc(), KnowledgeFact.created_at.desc())
            )
        )
        .scalars()
        .all()
    )
    live_facts = [
        fact
        for fact in all_facts
        if fact.status
        in (
            KnowledgeFactStatus.OBSERVED,
            KnowledgeFactStatus.VERIFIED,
            KnowledgeFactStatus.CONFLICTED,
        )
    ]

    current_by_subject: dict[tuple[KnowledgeSource, str], KnowledgeFact] = {}
    previous_by_subject: dict[tuple[KnowledgeSource, str], KnowledgeFact] = {}
    for fact in live_facts:  # newest first
        subject = (fact.source, fact.source_ref)
        existing = current_by_subject.get(subject)
        if existing is None or (
            existing.status is KnowledgeFactStatus.CONFLICTED
            and fact.status is not KnowledgeFactStatus.CONFLICTED
        ):
            current_by_subject[subject] = fact
    for fact in all_facts:  # newest first; superseded only
        if fact.status is KnowledgeFactStatus.SUPERSEDED:
            subject = (fact.source, fact.source_ref)
            if subject not in previous_by_subject:
                previous_by_subject[subject] = fact

    # Selection order: verified first, then newest first (stable two-pass sort).
    ordered = sorted(live_facts, key=lambda item: item.observed_at, reverse=True)
    ordered.sort(key=lambda item: 0 if item.status is KnowledgeFactStatus.VERIFIED else 1)

    selected_ids: set[uuid.UUID] = set()
    if entity_refs:
        for fact in ordered:
            if _fact_matches_entity(fact, entity_refs):
                selected_ids.add(fact.id)
    per_source_counts: dict[KnowledgeSource, int] = {}
    for fact in ordered:
        if fact.id in selected_ids:
            continue
        if per_source_counts.get(fact.source, 0) >= max_facts_per_source:
            continue
        per_source_counts[fact.source] = per_source_counts.get(fact.source, 0) + 1
        selected_ids.add(fact.id)
    selected_facts = [fact for fact in ordered if fact.id in selected_ids]

    fact_entries: list[dict[str, Any]] = []
    for fact in selected_facts:
        payload = _fact_payload(fact)
        subject = (fact.source, fact.source_ref)
        current = current_by_subject.get(subject)
        payload["current"] = current is not None and current.id == fact.id
        payload["entity_focus"] = bool(entity_refs) and _fact_matches_entity(fact, entity_refs)
        previous = previous_by_subject.get(subject)
        if payload["current"] and previous is not None:
            payload["previous"] = _snippet(previous.fact, _PREVIOUS_SNIPPET_CHARS)
        fact_entries.append(payload)

    decisions = list(
        (
            await session.execute(
                select(KnowledgeFact)
                .where(
                    KnowledgeFact.mission_id == mission.id,
                    KnowledgeFact.kind == KnowledgeFactKind.DECISION,
                    KnowledgeFact.status.in_(_LIVE_STATUSES),
                )
                .order_by(KnowledgeFact.observed_at.desc())
                .limit(max_decisions)
            )
        )
        .scalars()
        .all()
    )

    proposals = list(
        (
            await session.execute(
                select(ActionProposal)
                .where(ActionProposal.mission_id == mission.id)
                .order_by(ActionProposal.created_at.desc())
            )
        )
        .scalars()
        .all()
    )
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

    recent_actions: list[dict[str, Any]] = []
    pending_actions: list[dict[str, Any]] = []
    verified_outcomes: list[dict[str, Any]] = []
    completed_work: list[dict[str, Any]] = []
    remaining_work: list[dict[str, Any]] = []
    blockers: list[str] = []
    for proposal in proposals:
        execution = executions.get(proposal.id)
        verification = verifications.get(execution.id) if execution else None
        entry: dict[str, Any] = {
            "id": str(proposal.id),
            "provider": proposal.provider.value,
            "operation": proposal.operation,
            "rationale": proposal.rationale,
            "status": proposal.status,
        }
        if execution is not None:
            entry["execution_status"] = execution.status
            entry["external_id"] = execution.external_id
            entry["attempts"] = execution.attempts
            entry["last_error"] = (
                _snippet(execution.last_error, _ERROR_SNIPPET_CHARS)
                if execution.last_error
                else None
            )
        if verification is not None:
            entry["verification_status"] = verification.status
        verified = verification is not None and verification.status == "verified"
        if verified:
            completed_work.append(
                {
                    "provider": proposal.provider.value,
                    "operation": proposal.operation,
                    "external_id": execution.external_id if execution else None,
                }
            )
        else:
            remaining_work.append(
                {
                    "provider": proposal.provider.value,
                    "operation": proposal.operation,
                    "status": "not_started" if execution is None else execution.status,
                    "last_error": (
                        _snippet(execution.last_error, _ERROR_SNIPPET_CHARS)
                        if execution is not None and execution.last_error
                        else None
                    ),
                }
            )
            if execution is not None and execution.status == "failed" and execution.last_error:
                blockers.append(
                    f"{proposal.provider.value} {proposal.operation}: "
                    f"{_snippet(execution.last_error, _ERROR_SNIPPET_CHARS)}"
                )
        is_pending = proposal.status not in ("rejected", "cancelled", "verified") and (
            execution is None
            or execution.status in ("pending", "failed")
            or proposal.status in ("proposed", "pending")
        )
        if is_pending:
            pending_actions.append(entry)
        else:
            recent_actions.append(entry)
            if verified:
                verified_outcomes.append(entry)

    for fact in live_facts:
        if fact.status is KnowledgeFactStatus.CONFLICTED:
            reason = str(fact.data.get("conflict_reason") or fact.fact)
            blockers.append(
                f"{fact.source.value}:{fact.source_ref} — {_snippet(reason, _ERROR_SNIPPET_CHARS)}"
            )
    unique_blockers: list[str] = []
    for blocker in blockers:
        if blocker not in unique_blockers:
            unique_blockers.append(blocker)

    conflicts = [
        _fact_payload(fact) for fact in live_facts if fact.status is KnowledgeFactStatus.CONFLICTED
    ]

    bundles = list(
        (
            await session.execute(
                select(ApprovalBundle)
                .where(
                    ApprovalBundle.mission_id == mission.id,
                    ApprovalBundle.workspace_id == mission.workspace_id,
                )
                .order_by(ApprovalBundle.version.desc())
            )
        )
        .scalars()
        .all()
    )
    approval_section: dict[str, Any] | None = None
    if bundles:
        latest = bundles[0]
        action_count = int(
            await session.scalar(
                select(func.count())
                .select_from(ActionProposal)
                .where(ActionProposal.approval_bundle_id == latest.id)
            )
            or 0
        )
        approval_section = {
            "status": latest.status,
            "version": latest.version,
            "action_count": action_count,
            "decided_by_user_id": (
                str(latest.decided_by_user_id) if latest.decided_by_user_id else None
            ),
            "decided_at": latest.decided_at.isoformat() if latest.decided_at else None,
            "decision_note": latest.decision_note,
            "edit_history": [
                {
                    "version": bundle.version,
                    "status": bundle.status,
                    "decided_at": bundle.decided_at.isoformat() if bundle.decided_at else None,
                    "decision_note": bundle.decision_note,
                }
                for bundle in bundles[1:]
            ],
        }

    transitions = list(
        (
            await session.execute(
                select(MissionTransition)
                .where(MissionTransition.mission_id == mission.id)
                .order_by(MissionTransition.created_at.desc(), MissionTransition.id.desc())
                .limit(_MAX_TRANSITIONS)
            )
        )
        .scalars()
        .all()
    )
    recent_transitions = [
        {
            "from_status": item.from_status.value if item.from_status else None,
            "to_status": item.to_status.value,
            "reason": item.reason,
            "created_at": item.created_at.isoformat(),
        }
        for item in transitions
    ]

    pack: dict[str, Any] = {
        "task": mission.prompt,
        "mission_status": mission.status.value,
        "result_summary": mission.result_summary,
        "mission_status_summary": {
            "status": mission.status.value,
            "completed_work": completed_work,
            "remaining_work": remaining_work,
            "blockers": unique_blockers,
        },
        "approval": approval_section,
        "facts": fact_entries,
        "decisions": [_fact_payload(fact) for fact in decisions],
        "recent_actions": recent_actions[:max_actions],
        "pending_actions": pending_actions[:max_actions],
        "verified_outcomes": verified_outcomes[:max_actions],
        "conflicts": conflicts,
        "recent_transitions": recent_transitions,
    }
    _enforce_budget(pack, max_chars)
    return pack


async def kb_metrics(session: AsyncSession, mission: Mission) -> dict[str, int]:
    """Knowledge-quality counters for the dashboard (context/memory quality)."""
    facts = list(
        (
            await session.execute(
                select(KnowledgeFact).where(KnowledgeFact.mission_id == mission.id)
            )
        )
        .scalars()
        .all()
    )

    return {
        "total_facts": len(facts),
        "live_facts": sum(1 for fact in facts if fact.status in _LIVE_STATUSES),
        "verified_facts": sum(1 for fact in facts if fact.status is KnowledgeFactStatus.VERIFIED),
        "conflicted_facts": sum(
            1 for fact in facts if fact.status is KnowledgeFactStatus.CONFLICTED
        ),
        "superseded_facts": sum(
            1 for fact in facts if fact.status is KnowledgeFactStatus.SUPERSEDED
        ),
        "decisions": sum(1 for fact in facts if fact.kind is KnowledgeFactKind.DECISION),
    }


