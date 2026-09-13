"""K5 seam: context engine two-stage retrieval + connector capabilities."""

from __future__ import annotations

import asyncio
import uuid

from app.models import (
    KnowledgeFactKind,
    KnowledgeSource,
    Mission,
    MissionStatus,
    Project,
    User,
    Workspace,
)
from app.services.connectors import CONNECTOR_CAPABILITIES, can_propose_write, capabilities_for
from app.services.context_engine import search_context
from app.services.knowledge import record_fact


async def _seed(session) -> tuple[uuid.UUID, uuid.UUID]:
    workspace = Workspace(name="Engine Workspace", slug=f"eng-{uuid.uuid4().hex[:8]}")
    user = User(
        email=f"eng-{uuid.uuid4().hex[:8]}@example.com",
        password_hash="x",
        display_name="Engine Tester",
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
        prompt="Handle the payment release",
        project_name=project.name,
        status=MissionStatus.COMPLETED,
        correlation_id=uuid.uuid4(),
    )
    session.add(mission)
    await session.flush()

    await record_fact(
        session,
        mission,
        kind=KnowledgeFactKind.SOURCE_FACT,
        source=KnowledgeSource.JIRA,
        source_ref="PAY-18",
        fact="PAY-18: Issue status is Done",
    )
    await record_fact(
        session,
        mission,
        kind=KnowledgeFactKind.SOURCE_FACT,
        source=KnowledgeSource.GITHUB,
        source_ref="42",
        fact="PR #42 modifies payment retry logic",
    )
    await record_fact(
        session,
        mission,
        kind=KnowledgeFactKind.SOURCE_FACT,
        source=KnowledgeSource.SLACK,
        source_ref="msg-7",
        fact="Slack confirms retry behavior changed in payments",
    )
    return workspace.id, project.id


def test_exact_entity_match_outranks_text_match(client) -> None:
    factory = client.test_session_factory  # type: ignore[attr-defined]

    async def scenario() -> list[tuple[str, float]]:
        async with factory() as session:
            workspace_id, project_id = await _seed(session)

            results = await search_context(
                session,
                workspace_id,
                project_id,
                query="payment release status",
                entities=["PAY-18"],
                limit=20,
            )
            assert results[0].source_ref == "PAY-18"
            assert results[0].score == 1.0
            return [(r.source_ref, r.score) for r in results]

    matches = asyncio.run(scenario())
    # Text stage also matched the payment-related facts.
    assert ("42", 0.5) in matches or any(ref == "42" for ref, _ in matches)
    assert all(score <= 1.0 for _, score in matches)


def test_text_search_matches_tokens_and_ranks_by_coverage(client) -> None:
    factory = client.test_session_factory  # type: ignore[attr-defined]

    async def scenario() -> list[tuple[str, float]]:
        async with factory() as session:
            workspace_id, project_id = await _seed(session)

            results = await search_context(
                session,
                workspace_id,
                project_id,
                query="payment retry changed",
                entities=None,
                limit=20,
            )
            return [(r.source_ref, r.score) for r in results]

    matches = asyncio.run(scenario())
    # Text-stage score = 0.5 x token coverage. GitHub covers 2/3 tokens,
    # Slack covers 3/3; PAY-18 covers none and is excluded.
    by_ref = dict(matches)
    assert by_ref["42"] == 0.5 * (2 / 3)
    assert by_ref["msg-7"] == 0.5
    assert "PAY-18" not in by_ref


def test_search_is_scoped_to_project_and_respects_limit(client) -> None:
    factory = client.test_session_factory  # type: ignore[attr-defined]

    async def scenario() -> tuple[int, int]:
        async with factory() as session:
            workspace_id, project_id = await _seed(session)

            results = await search_context(
                session,
                workspace_id,
                project_id,
                query="payment",
                limit=2,
            )
            limited = len(results)

            empty = await search_context(
                session,
                workspace_id,
                uuid.uuid4(),  # different project
                query="payment",
            )
            return limited, len(empty)

    limited, empty = asyncio.run(scenario())
    assert limited == 2
    assert empty == 0


def test_connector_capabilities_registry() -> None:
    assert CONNECTOR_CAPABILITIES["github"].can_read is True
    assert CONNECTOR_CAPABILITIES["github"].can_write is False
    assert CONNECTOR_CAPABILITIES["github"].can_verify is True

    for provider in ("jira", "slack", "notion"):
        caps = CONNECTOR_CAPABILITIES[provider]
        assert caps.can_read and caps.can_write and caps.can_verify

    assert can_propose_write("jira") is True
    assert can_propose_write("GITHUB") is False
    assert capabilities_for("unknown") is None
