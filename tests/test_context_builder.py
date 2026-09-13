"""Context Builder v2: status summary, approval visibility, freshness, entity focus, budget."""

from __future__ import annotations

import asyncio
import json
import uuid
from datetime import UTC, datetime

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    ActionProposal,
    AgentAssessment,
    AgentRun,
    ApprovalBundle,
    ContextPack,
    ExecutionRecord,
    IntegrationProvider,
    KnowledgeFactKind,
    KnowledgeSource,
    Mission,
    MissionStatus,
    MissionTransition,
    Project,
    User,
    VerificationRecord,
    Workspace,
)
from app.services.knowledge import build_mission_context, record_fact

PROMPT = "Synchronize PAY-18 and notify #payments about the release"


async def _make_mission(session: AsyncSession, prompt: str = PROMPT) -> Mission:
    workspace = Workspace(name="CB Workspace", slug=f"cb-{uuid.uuid4().hex[:8]}")
    user = User(
        email=f"cb-{uuid.uuid4().hex[:8]}@example.com",
        password_hash="x",
        display_name="CB Tester",
    )
    session.add_all([workspace, user])
    await session.flush()
    project = Project(workspace_id=workspace.id, name="Payments")
    session.add(project)
    await session.flush()
    mission = Mission(
        workspace_id=workspace.id,
        created_by_user_id=user.id,
        project_id=project.id,
        prompt=prompt,
        project_name="Payments",
        status=MissionStatus.PARTIALLY_COMPLETE,
        correlation_id=uuid.uuid4(),
    )
    session.add(mission)
    await session.flush()
    return mission


async def _make_approval_chain(session: AsyncSession, mission: Mission) -> ApprovalBundle:
    """Create ContextPack -> AgentRun -> Assessment -> bundles; return the approved bundle."""
    context_pack = ContextPack(
        workspace_id=mission.workspace_id,
        mission_id=mission.id,
        version=1,
        summary="pack",
        content={},
        content_hash="hash",
    )
    session.add(context_pack)
    await session.flush()
    agent_run = AgentRun(
        workspace_id=mission.workspace_id,
        mission_id=mission.id,
        context_pack_id=context_pack.id,
        mode="fallback",
        status="completed",
        request_payload={},
        response_payload={},
    )
    session.add(agent_run)
    await session.flush()
    assessment = AgentAssessment(
        workspace_id=mission.workspace_id,
        mission_id=mission.id,
        agent_run_id=agent_run.id,
        context_summary="summary",
        risk_level="low",
        risk_factors=[],
        review_effort_minutes=10,
        effort_rationale="rationale",
        confidence=0.9,
        explanation="explanation",
        reviewer_candidates=[],
        citations=[],
        proposals=[],
    )
    session.add(assessment)
    await session.flush()
    for version, status, note in ((1, "revised", "Reduced scope"), (2, "approved", "Ship it")):
        bundle = ApprovalBundle(
            workspace_id=mission.workspace_id,
            mission_id=mission.id,
            assessment_id=assessment.id,
            version=version,
            status=status,
            policy_result={"allowed": True, "approval_required": True, "reasons": []},
            decision_note=note,
        )
        session.add(bundle)
        await session.flush()
    return bundle


async def _add_action(
    session: AsyncSession,
    bundle: ApprovalBundle,
    mission: Mission,
    sequence: int,
    provider: IntegrationProvider,
    operation: str,
    *,
    execution_status: str | None,
    external_id: str | None = None,
    last_error: str | None = None,
    attempts: int = 0,
    verified: bool = False,
) -> None:
    action = ActionProposal(
        workspace_id=mission.workspace_id,
        mission_id=mission.id,
        approval_bundle_id=bundle.id,
        sequence=sequence,
        provider=provider,
        operation=operation,
        rationale="rationale",
        payload={},
        citations=["notion:page:mission-input"],
        status="verified" if verified else "approved",
    )
    session.add(action)
    await session.flush()
    if execution_status is None:
        return
    execution = ExecutionRecord(
        workspace_id=mission.workspace_id,
        mission_id=mission.id,
        action_proposal_id=action.id,
        idempotency_key=f"action:{action.id}",
        status=execution_status,
        attempts=attempts,
        external_id=external_id,
        last_error=last_error,
    )
    session.add(execution)
    await session.flush()
    if verified:
        session.add(
            VerificationRecord(
                workspace_id=mission.workspace_id,
                mission_id=mission.id,
                execution_id=execution.id,
                status="verified",
                evidence={"external_id": external_id},
                checked_at=datetime.now(UTC),
            )
        )


def test_status_summary_approval_and_enriched_actions(client: TestClient) -> None:
    factory = client.test_session_factory  # type: ignore[attr-defined]

    async def scenario() -> None:
        async with factory() as session:
            mission = await _make_mission(session)
            bundle = await _make_approval_chain(session, mission)
            await _add_action(
                session,
                bundle,
                mission,
                1,
                IntegrationProvider.JIRA,
                "issue.create",
                execution_status="verified",
                external_id="PAY-19",
                attempts=1,
                verified=True,
            )
            await _add_action(
                session,
                bundle,
                mission,
                2,
                IntegrationProvider.SLACK,
                "message.post",
                execution_status="failed",
                attempts=3,
                last_error="Temporary Slack error",
            )
            await _add_action(
                session,
                bundle,
                mission,
                3,
                IntegrationProvider.NOTION,
                "page.append",
                execution_status=None,
            )
            session.add(
                MissionTransition(
                    workspace_id=mission.workspace_id,
                    mission_id=mission.id,
                    from_status=MissionStatus.RUNNING,
                    to_status=MissionStatus.PARTIALLY_COMPLETE,
                    reason="Execution finished: 1 verified, 1 failed",
                )
            )
            await session.commit()

            context = await build_mission_context(session, mission)

            summary = context["mission_status_summary"]
            assert summary["status"] == "partially_complete"
            assert summary["completed_work"] == [
                {"provider": "jira", "operation": "issue.create", "external_id": "PAY-19"}
            ]
            remaining = {
                (item["provider"], item["operation"]): item
                for item in summary["remaining_work"]
            }
            assert set(remaining) == {("slack", "message.post"), ("notion", "page.append")}
            assert remaining[("slack", "message.post")]["status"] == "failed"
            assert "Temporary Slack error" in remaining[("slack", "message.post")]["last_error"]
            assert remaining[("notion", "page.append")]["status"] == "not_started"
            assert any("Temporary Slack error" in blocker for blocker in summary["blockers"])

            approval = context["approval"]
            assert approval is not None
            assert approval["status"] == "approved"
            assert approval["version"] == 2
            assert approval["action_count"] == 3
            assert approval["decision_note"] == "Ship it"
            assert [item["version"] for item in approval["edit_history"]] == [1]

            slack_entry = next(
                item for item in context["pending_actions"] if item["provider"] == "slack"
            )
            assert slack_entry["execution_status"] == "failed"
            assert slack_entry["attempts"] == 3
            assert "Temporary Slack error" in slack_entry["last_error"]
            notion_entry = next(
                item for item in context["pending_actions"] if item["provider"] == "notion"
            )
            assert notion_entry["status"] == "approved"  # approved but not started → remaining
            jira_entry = next(
                item for item in context["recent_actions"] if item["provider"] == "jira"
            )
            assert jira_entry["verification_status"] == "verified"

            transitions = context["recent_transitions"]
            assert transitions[0]["to_status"] == "partially_complete"
            assert "1 verified, 1 failed" in transitions[0]["reason"]

    asyncio.run(scenario())


def test_failed_action_reappears_as_pending_after_retry_reset(client: TestClient) -> None:
    """After POST /retry resets a failed execution, the context shows it as pending work."""
    factory = client.test_session_factory  # type: ignore[attr-defined]

    async def scenario() -> None:
        async with factory() as session:
            mission = await _make_mission(session)
            bundle = await _make_approval_chain(session, mission)
            await _add_action(
                session,
                bundle,
                mission,
                1,
                IntegrationProvider.SLACK,
                "message.post",
                execution_status="failed",
                attempts=3,
                last_error="Temporary Slack error",
            )
            await session.commit()
            # Simulate the retry endpoint's reset (executions.py resets failed rows).
            execution = (
                await session.execute(select(ExecutionRecord))
            ).scalar_one()
            execution.status = "pending"
            execution.attempts = 0
            execution.last_error = None
            await session.commit()

            context = await build_mission_context(session, mission)
            slack = context["pending_actions"][0]
            assert slack["execution_status"] == "pending"
            assert slack["attempts"] == 0
            assert slack["last_error"] is None
            assert context["mission_status_summary"]["remaining_work"][0]["status"] == "pending"

    asyncio.run(scenario())


def test_fresh_fact_supersedes_historical_in_context(client: TestClient) -> None:
    factory = client.test_session_factory  # type: ignore[attr-defined]

    async def scenario() -> None:
        async with factory() as session:
            mission = await _make_mission(session)
            await record_fact(
                session,
                mission,
                kind=KnowledgeFactKind.SOURCE_FACT,
                source=KnowledgeSource.JIRA,
                source_ref="PAY-18",
                fact="PAY-18 is In Progress",
            )
            await record_fact(
                session,
                mission,
                kind=KnowledgeFactKind.SOURCE_FACT,
                source=KnowledgeSource.JIRA,
                source_ref="PAY-18",
                fact="PAY-18 is Done",
            )
            await session.commit()

            context = await build_mission_context(session, mission)
            pay_facts = [item for item in context["facts"] if item["source_ref"] == "PAY-18"]
            assert len(pay_facts) == 1
            assert pay_facts[0]["fact"] == "PAY-18 is Done"
            assert pay_facts[0]["current"] is True
            assert pay_facts[0]["previous"] == "PAY-18 is In Progress"

    asyncio.run(scenario())


def test_entity_facts_survive_source_caps(client: TestClient) -> None:
    factory = client.test_session_factory  # type: ignore[attr-defined]

    async def scenario() -> None:
        async with factory() as session:
            mission = await _make_mission(session)
            # PAY-18 is the entity from the prompt but the oldest fact: without
            # entity focus the newest-first per-source cap would drop it.
            await record_fact(
                session,
                mission,
                kind=KnowledgeFactKind.SOURCE_FACT,
                source=KnowledgeSource.JIRA,
                source_ref="PAY-18",
                fact="PAY-18 is Done",
            )
            for index in range(1, 9):
                await record_fact(
                    session,
                    mission,
                    kind=KnowledgeFactKind.SOURCE_FACT,
                    source=KnowledgeSource.JIRA,
                    source_ref=f"PAY-{index}",
                    fact=f"Jira fact number {index}",
                )
            await session.commit()

            context = await build_mission_context(session, mission)
            refs = [item["source_ref"] for item in context["facts"]]
            assert "PAY-18" in refs
            assert len(refs) == 7  # 6 per-source cap + 1 entity-focused
            entity_fact = next(item for item in context["facts"] if item["source_ref"] == "PAY-18")
            assert entity_fact["entity_focus"] is True
            assert all(
                item.get("entity_focus") is False
                for item in context["facts"]
                if item["source_ref"] != "PAY-18"
            )

    asyncio.run(scenario())


def test_context_respects_character_budget(client: TestClient) -> None:
    factory = client.test_session_factory  # type: ignore[attr-defined]

    async def scenario() -> None:
        async with factory() as session:
            mission = await _make_mission(session)
            sources = (
                KnowledgeSource.JIRA,
                KnowledgeSource.GITHUB,
                KnowledgeSource.NOTION,
                KnowledgeSource.SLACK,
            )
            for index in range(40):
                await record_fact(
                    session,
                    mission,
                    kind=KnowledgeFactKind.SOURCE_FACT,
                    source=sources[index % 4],
                    source_ref=f"BIG-{index}",
                    fact="x" * 600,
                )
            await session.commit()

            context = await build_mission_context(session, mission)
            assert len(json.dumps(context, default=str)) <= 12_000
            assert context["task"] == PROMPT
            assert "mission_status_summary" in context
            assert len(context["facts"]) >= 10  # trimmed, not emptied

    asyncio.run(scenario())


def test_empty_mission_context_has_nulls_and_empty_sections(client: TestClient) -> None:
    factory = client.test_session_factory  # type: ignore[attr-defined]

    async def scenario() -> None:
        async with factory() as session:
            mission = await _make_mission(session)
            await session.commit()

            context = await build_mission_context(session, mission)
            assert context["approval"] is None
            assert context["recent_transitions"] == []
            assert context["mission_status_summary"]["remaining_work"] == []
            assert context["mission_status_summary"]["completed_work"] == []
            assert context["mission_status_summary"]["blockers"] == []

    asyncio.run(scenario())
