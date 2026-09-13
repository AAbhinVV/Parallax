"""K4.4 event router + K4.3 waiting/wake: dedupe, discovery, wake."""

from __future__ import annotations

import asyncio
import uuid
from typing import Any

from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.models import (
    KnowledgeFactKind,
    KnowledgeSource,
    Mission,
    MissionStatus,
    OutboxJob,
    Project,
    User,
    Workspace,
)
from app.services.event_router import route_event
from app.services.knowledge import record_fact


async def _make_workspace(session) -> tuple[Workspace, User, Project]:
    workspace = Workspace(name="Event Workspace", slug=f"evt-{uuid.uuid4().hex[:8]}")
    user = User(
        email=f"evt-{uuid.uuid4().hex[:8]}@example.com",
        password_hash="x",
        display_name="Event Tester",
    )
    session.add_all([workspace, user])
    await session.flush()
    project = Project(workspace_id=workspace.id, name="Payments")
    session.add(project)
    await session.flush()
    return workspace, user, project


async def _make_mission(
    session,
    workspace: Workspace,
    user: User,
    project: Project,
    status: MissionStatus,
) -> Mission:
    mission = Mission(
        workspace_id=workspace.id,
        created_by_user_id=user.id,
        project_id=project.id,
        prompt="Handle the payment release",
        project_name=project.name,
        status=status,
        correlation_id=uuid.uuid4(),
    )
    session.add(mission)
    await session.flush()
    return mission


def test_event_wakes_waiting_mission_and_queues_execution(client: TestClient) -> None:
    factory = client.test_session_factory  # type: ignore[attr-defined]

    async def scenario() -> None:
        async with factory() as session:
            workspace, user, project = await _make_workspace(session)
            mission = await _make_mission(
                session, workspace, user, project, MissionStatus.WAITING_FOR_EVENT
            )
            await record_fact(
                session,
                mission,
                kind=KnowledgeFactKind.SOURCE_FACT,
                source=KnowledgeSource.JIRA,
                source_ref="PAY-18",
                fact="PAY-18 is In Progress",
            )
            await session.commit()

            woken = await route_event(
                session,
                provider="jira",
                event_type="issue_updated",
                external_id="PAY-18",
                payload={"status": "Done"},
            )
            await session.commit()
            assert woken == [mission.id]

            refreshed = await session.get(Mission, mission.id)
            assert refreshed is not None
            assert refreshed.status == MissionStatus.RUNNING

            jobs = (
                (
                    await session.execute(
                        select(OutboxJob).where(OutboxJob.mission_id == mission.id)
                    )
                )
                .scalars()
                .all()
            )
            assert len(jobs) == 1
            assert jobs[0].job_type == "execute_mission"

    asyncio.run(scenario())


def test_event_is_deduplicated_on_replay(client: TestClient) -> None:
    factory = client.test_session_factory  # type: ignore[attr-defined]

    async def scenario() -> tuple[int, int]:
        async with factory() as session:
            workspace, user, project = await _make_workspace(session)
            mission = await _make_mission(
                session, workspace, user, project, MissionStatus.WAITING_FOR_EVENT
            )
            await record_fact(
                session,
                mission,
                kind=KnowledgeFactKind.SOURCE_FACT,
                source=KnowledgeSource.GITHUB,
                source_ref="42",
                fact="PR #42 changes payment retry logic",
            )
            await session.commit()

            first = await route_event(
                session,
                provider="github",
                event_type="pull_request",
                external_id="42",
                payload={"action": "updated"},
            )
            await session.commit()

            # Replay of the same event delivery: ignored.
            second = await route_event(
                session,
                provider="github",
                event_type="pull_request",
                external_id="42",
                payload={"action": "updated"},
            )
            await session.commit()

            job_count = (
                await session.execute(
                    select(func.count())
                    .select_from(OutboxJob)
                    .where(OutboxJob.mission_id == mission.id)
                )
            ).scalar_one()
            return len(first), len(second), job_count

    first_len, second_len, job_count = asyncio.run(scenario())
    assert first_len == 1
    assert second_len == 0
    assert job_count == 1


def test_event_ignores_unknown_missions_and_providers(client: TestClient) -> None:
    factory = client.test_session_factory  # type: ignore[attr-defined]

    async def scenario() -> None:
        async with factory() as session:
            workspace, user, project = await _make_workspace(session)
            # COMPLETED missions are never woken; unknown provider routes nowhere.
            completed = await _make_mission(
                session, workspace, user, project, MissionStatus.COMPLETED
            )
            await record_fact(
                session,
                completed,
                kind=KnowledgeFactKind.SOURCE_FACT,
                source=KnowledgeSource.NOTION,
                source_ref="page-1",
                fact="Release checklist exists",
            )
            await session.commit()

            woken = await route_event(
                session,
                provider="notion",
                event_type="page_updated",
                external_id="page-1",
                payload={},
            )
            await session.commit()
            assert woken == []

            woken = await route_event(
                session,
                provider="pagerduty",
                event_type="incident",
                external_id="INC-1",
                payload={},
            )
            await session.commit()
            assert woken == []

    asyncio.run(scenario())


def test_wait_endpoint_parks_mission_and_event_wakes_it(client: TestClient) -> None:
    from tests.test_missions import headers, register

    token = str(register(client)["access_token"])
    created = client.post(
        "/api/missions",
        json={"prompt": "Wait for the payment release event", "project": "General"},
        headers=headers(token),
    )
    assert created.status_code == 202
    mission_id = created.json()["id"]

    factory = client.test_session_factory  # type: ignore[attr-defined]

    async def set_running() -> None:
        async with factory() as session:
            mission = await session.get(Mission, uuid.UUID(mission_id))
            assert mission is not None
            mission.status = MissionStatus.RUNNING
            await session.commit()

    asyncio.run(set_running())

    parked = client.post(f"/api/missions/{mission_id}/wait", headers=headers(token))
    assert parked.status_code == 200
    assert parked.json()["status"] == "waiting_for_event"

    # Register a KB fact for the mission so the event can find it.
    async def add_fact() -> None:
        async with factory() as session:
            mission = await session.get(Mission, uuid.UUID(mission_id))
            assert mission is not None
            await record_fact(
                session,
                mission,
                kind=KnowledgeFactKind.SOURCE_FACT,
                source=KnowledgeSource.SLACK,
                source_ref="msg-99",
                fact="Release discussion in #payments",
            )
            await session.commit()

    asyncio.run(add_fact())

    routed = client.post(
        "/api/webhooks/slack",
        json={"event_type": "message", "external_id": "msg-99", "payload": {}},
        headers=headers(token),
    )
    assert routed.status_code == 200
    assert routed.json()["woken_missions"] == [mission_id]

    mission = client.get(f"/api/missions/{mission_id}", headers=headers(token)).json()
    assert mission["status"] == "running"

    async def assert_outbox() -> None:
        async with factory() as session:
            jobs = (
                (
                    await session.execute(
                        select(OutboxJob).where(
                            OutboxJob.mission_id == uuid.UUID(mission_id),
                            OutboxJob.job_type == "execute_mission",
                        )
                    )
                )
                .scalars()
                .all()
            )
            assert len(jobs) == 1

    asyncio.run(assert_outbox())
