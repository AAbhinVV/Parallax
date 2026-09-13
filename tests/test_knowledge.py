"""Knowledge base semantics: append-only facts, supersede, provenance, context pack."""

from __future__ import annotations

import asyncio
import uuid

from app.models import (
    KnowledgeFactKind,
    KnowledgeFactStatus,
    KnowledgeSource,
    Mission,
    Project,
    User,
    Workspace,
)
from app.services.knowledge import (
    build_mission_context,
    kb_metrics,
    mark_fact_conflicted,
    mark_fact_verified,
    record_fact,
)


async def _make_mission(session) -> Mission:
    workspace = Workspace(name="KB Workspace", slug=f"kb-{uuid.uuid4().hex[:8]}")
    user = User(
        email=f"kb-{uuid.uuid4().hex[:8]}@example.com",
        password_hash="x",
        display_name="KB Tester",
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
        prompt="Review payment PR and synchronize tracking",
        project_name="Payments",
        correlation_id=uuid.uuid4(),
    )
    session.add(mission)
    await session.flush()
    return mission


def test_record_fact_is_idempotent_for_identical_value(client) -> None:
    factory = client.test_session_factory

    async def scenario() -> None:
        async with factory() as session:
            mission = await _make_mission(session)
            first = await record_fact(
                session,
                mission,
                kind=KnowledgeFactKind.SOURCE_FACT,
                source=KnowledgeSource.JIRA,
                source_ref="PAY-18",
                fact="PAY-18 is In Progress",
            )
            second = await record_fact(
                session,
                mission,
                kind=KnowledgeFactKind.SOURCE_FACT,
                source=KnowledgeSource.JIRA,
                source_ref="PAY-18",
                fact="PAY-18 is In Progress",
            )
            assert first.id == second.id
            assert second.status is KnowledgeFactStatus.OBSERVED
            metrics = await kb_metrics(session, mission)
            assert metrics["total_facts"] == 1
            await session.commit()

    asyncio.run(scenario())


def test_new_value_supersedes_old_fact_without_deleting_it(client) -> None:
    factory = client.test_session_factory

    async def scenario() -> None:
        async with factory() as session:
            mission = await _make_mission(session)
            stale = await record_fact(
                session,
                mission,
                kind=KnowledgeFactKind.SOURCE_FACT,
                source=KnowledgeSource.JIRA,
                source_ref="PAY-18",
                fact="PAY-18 is In Progress",
            )
            fresh = await record_fact(
                session,
                mission,
                kind=KnowledgeFactKind.SOURCE_FACT,
                source=KnowledgeSource.JIRA,
                source_ref="PAY-18",
                fact="PAY-18 is Done",
            )
            assert stale.status is KnowledgeFactStatus.SUPERSEDED
            assert stale.superseded_by_id == fresh.id
            assert fresh.status is KnowledgeFactStatus.OBSERVED
            metrics = await kb_metrics(session, mission)
            assert metrics["total_facts"] == 2
            assert metrics["superseded_facts"] == 1
            assert metrics["live_facts"] == 1
            await session.commit()

    asyncio.run(scenario())


def test_verified_and_conflicted_transitions(client) -> None:
    factory = client.test_session_factory

    async def scenario() -> None:
        async with factory() as session:
            mission = await _make_mission(session)
            fact = await record_fact(
                session,
                mission,
                kind=KnowledgeFactKind.SOURCE_FACT,
                source=KnowledgeSource.SLACK,
                source_ref="msg-1",
                fact="Completion message posted to #payments",
            )
            mark_fact_verified(session, fact)
            assert fact.status is KnowledgeFactStatus.VERIFIED
            assert fact.verified_at is not None

            conflict = await record_fact(
                session,
                mission,
                kind=KnowledgeFactKind.SOURCE_FACT,
                source=KnowledgeSource.JIRA,
                source_ref="PAY-18",
                fact="PAY-18 is Done",
            )
            mark_fact_conflicted(session, conflict, reason="Jira contradicted memory")
            assert conflict.status is KnowledgeFactStatus.CONFLICTED
            assert conflict.data["conflict_reason"] == "Jira contradicted memory"
            await session.commit()

    asyncio.run(scenario())


def test_decisions_are_kept_out_of_source_facts(client) -> None:
    factory = client.test_session_factory

    async def scenario() -> None:
        async with factory() as session:
            mission = await _make_mission(session)
            await record_fact(
                session,
                mission,
                kind=KnowledgeFactKind.SOURCE_FACT,
                source=KnowledgeSource.GITHUB,
                source_ref="PR-42",
                fact="PR #42 modifies payment retry logic",
            )
            await record_fact(
                session,
                mission,
                kind=KnowledgeFactKind.DECISION,
                source=KnowledgeSource.AGENT,
                source_ref="agent-run:1",
                fact="Jira tracking must be synchronized",
                confidence=0.94,
            )
            context = await build_mission_context(session, mission)
            assert context["task"] == "Review payment PR and synchronize tracking"
            assert [item["source_ref"] for item in context["facts"]] == ["PR-42"]
            assert [item["kind"] for item in context["decisions"]] == ["decision"]
            assert context["decisions"][0]["confidence"] == 0.94
            metrics = await kb_metrics(session, mission)
            assert metrics["decisions"] == 1
            await session.commit()

    asyncio.run(scenario())


def test_context_pack_caps_facts_per_source(client) -> None:
    factory = client.test_session_factory

    async def scenario() -> None:
        async with factory() as session:
            mission = await _make_mission(session)
            for index in range(10):
                await record_fact(
                    session,
                    mission,
                    kind=KnowledgeFactKind.SOURCE_FACT,
                    source=KnowledgeSource.JIRA,
                    source_ref=f"PAY-{index}",
                    fact=f"Jira fact number {index}",
                )
            context = await build_mission_context(session, mission)
            jira_facts = [item for item in context["facts"] if item["source"] == "jira"]
            assert len(jira_facts) == 6  # default per-source cap
            await session.commit()

    asyncio.run(scenario())


