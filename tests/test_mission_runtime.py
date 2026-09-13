"""K4.1 durable mission runtime: leases, recovery, resume, step state."""

from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.integrations.contracts import AdapterError
from app.models import (
    ActionProposal,
    ApprovalBundle,
    ExecutionRecord,
    IntegrationProvider,
    Mission,
    MissionStatus,
    MissionStep,
)
from app.services import execution as execution_service
from app.services.execution import execute_mission
from app.services.mission_runtime import (
    claim_mission,
    get_runnable_actions,
    recover_expired_missions,
    release_lease,
    renew_lease,
)
from app.worker import prepare_mission

OWNER = {
    "email": "runtime-owner@example.com",
    "password": "correct-horse-battery-staple",
    "display_name": "Runtime Owner",
    "workspace_name": "Runtime Workspace",
    "workspace_slug": "runtime-workspace",
}


def auth(client: TestClient) -> dict[str, str]:
    response = client.post("/api/auth/register", json=OWNER)
    assert response.status_code == 201
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def created_mission(client: TestClient, headers: dict[str, str]) -> str:
    return str(
        client.post(
            "/api/missions",
            json={"prompt": "Handle the durable payment release", "project": "General"},
            headers=headers,
        ).json()["id"]
    )


def prepared_mission(client: TestClient, headers: dict[str, str]) -> str:
    mission_id = created_mission(client, headers)
    factory = client.test_session_factory  # type: ignore[attr-defined]
    assert (
        asyncio.run(prepare_mission({"session_factory": factory}, mission_id))
        == "context_collected"
    )
    return mission_id


class FakeRedis:
    locked = False

    async def set(self, *_: object, **__: object) -> bool:
        if self.locked:
            return False
        self.locked = True
        return True

    async def eval(self, *_: object) -> int:
        self.locked = False
        return 1


def test_claim_lease_is_exclusive_and_expires(client: TestClient) -> None:
    factory = client.test_session_factory  # type: ignore[attr-defined]
    headers = auth(client)
    mission_id = created_mission(client, headers)

    async def scenario() -> None:
        async with factory() as session:
            assert await claim_mission(session, uuid.UUID(mission_id), "worker-a")
            await session.commit()

            # A different worker cannot claim a live lease.
            async with factory() as session:
                assert not await claim_mission(session, uuid.UUID(mission_id), "worker-b")
                await session.commit()

            # The owning worker can renew.
            async with factory() as session:
                assert await renew_lease(session, uuid.UUID(mission_id), "worker-a")
                assert not await renew_lease(session, uuid.UUID(mission_id), "worker-b")
                await session.commit()

            # Release, then reclaim by another worker.
            async with factory() as session:
                await release_lease(session, uuid.UUID(mission_id), "worker-b")  # no-op
                await release_lease(session, uuid.UUID(mission_id), "worker-a")
                await session.commit()

            async with factory() as session:
                assert await claim_mission(session, uuid.UUID(mission_id), "worker-b")
                await session.commit()

            # An expired lease is reclaimable.
            async with factory() as session:
                mission = await session.get(Mission, uuid.UUID(mission_id))
                assert mission is not None
                mission.lease_expires_at = datetime.now(UTC) - timedelta(seconds=1)
                await session.commit()

            async with factory() as session:
                assert await claim_mission(session, uuid.UUID(mission_id), "worker-a")
                await session.commit()

    asyncio.run(scenario())


def test_recover_expired_missions(client: TestClient) -> None:
    factory = client.test_session_factory  # type: ignore[attr-defined]
    headers = auth(client)
    expired_id = created_mission(client, headers)
    live_id = created_mission(client, headers)

    async def scenario() -> list[uuid.UUID]:
        async with factory() as session:
            expired = await session.get(Mission, uuid.UUID(expired_id))
            assert expired is not None
            expired.status = MissionStatus.RUNNING
            expired.worker_id = "dead-worker"
            expired.lease_expires_at = datetime.now(UTC) - timedelta(seconds=5)
            live = await session.get(Mission, uuid.UUID(live_id))
            assert live is not None
            live.status = MissionStatus.RUNNING
            live.worker_id = "live-worker"
            live.lease_expires_at = datetime.now(UTC) + timedelta(seconds=60)
            await session.commit()

        async with factory() as session:
            recovered = await recover_expired_missions(session)
            await session.commit()
            return recovered

    recovered = asyncio.run(scenario())
    assert uuid.UUID(expired_id) in recovered
    assert uuid.UUID(live_id) not in recovered

    async def assert_cleared() -> None:
        async with factory() as session:
            mission = await session.get(Mission, uuid.UUID(expired_id))
            assert mission is not None
            assert mission.worker_id is None
            assert mission.lease_expires_at is None
            # The mission stays RUNNING: it is still owned work.
            assert mission.status == MissionStatus.RUNNING

    asyncio.run(assert_cleared())


def test_runnable_actions_skip_verified_and_exclude_maxed_out(client: TestClient) -> None:
    factory = client.test_session_factory  # type: ignore[attr-defined]
    headers = auth(client)
    mission_id = created_mission(client, headers)

    async def scenario() -> list[str]:
        async with factory() as session:
            mission = await session.get(Mission, uuid.UUID(mission_id))
            assert mission is not None
            bundle = ApprovalBundle(
                workspace_id=mission.workspace_id,
                mission_id=mission.id,
                assessment_id=uuid.uuid4(),
                version=1,
                status="approved",
                policy_result={},
            )
            session.add(bundle)
            await session.flush()
            actions: list[ActionProposal] = []
            for index, (provider, operation) in enumerate(
                [
                    (IntegrationProvider.JIRA, "issue.create"),
                    (IntegrationProvider.SLACK, "message.post"),
                    (IntegrationProvider.NOTION, "page.append"),
                    (IntegrationProvider.JIRA, "issue.update"),
                ],
                start=1,
            ):
                action = ActionProposal(
                    workspace_id=mission.workspace_id,
                    mission_id=mission.id,
                    approval_bundle_id=bundle.id,
                    sequence=index,
                    provider=provider,
                    operation=operation,
                    rationale="runtime test",
                    payload={},
                    citations=[],
                )
                session.add(action)
                actions.append(action)
            await session.flush()

            # action 1: verified; action 2: failed under the cap;
            # action 3: failed at max attempts; action 4: not started.
            session.add(
                ExecutionRecord(
                    workspace_id=mission.workspace_id,
                    mission_id=mission.id,
                    action_proposal_id=actions[0].id,
                    idempotency_key=f"action:{actions[0].id}",
                    status="verified",
                    attempts=1,
                    external_id="PAY-1",
                )
            )
            session.add(
                ExecutionRecord(
                    workspace_id=mission.workspace_id,
                    mission_id=mission.id,
                    action_proposal_id=actions[1].id,
                    idempotency_key=f"action:{actions[1].id}",
                    status="failed",
                    attempts=1,
                    last_error="Temporary failure",
                )
            )
            session.add(
                ExecutionRecord(
                    workspace_id=mission.workspace_id,
                    mission_id=mission.id,
                    action_proposal_id=actions[2].id,
                    idempotency_key=f"action:{actions[2].id}",
                    status="failed",
                    attempts=3,
                    last_error="Exhausted",
                )
            )
            await session.commit()

            runnable = await get_runnable_actions(session, mission)
            return [action.operation for action in runnable]

    runnable = asyncio.run(scenario())
    # Verified action is skipped; maxed-out failure waits for /retry;
    # the failed-under-cap action and the unstarted action run.
    assert runnable == ["message.post", "issue.update"]


def test_step_state_survives_failure_and_resume(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = auth(client)
    mission_id = prepared_mission(client, headers)
    bundle = client.post(f"/api/missions/{mission_id}/approval", headers=headers).json()
    approved = client.post(
        f"/api/approvals/{bundle['id']}/approve", headers=headers, json={}
    )
    assert approved.status_code == 200
    factory = client.test_session_factory  # type: ignore[attr-defined]
    original_execute = execution_service._execute

    async def fail_slack(action: Any, approval: Any) -> Any:
        if action.provider == IntegrationProvider.SLACK:
            raise AdapterError(IntegrationProvider.SLACK, "Temporary Slack error", retryable=True)
        return await original_execute(action, approval)

    redis = FakeRedis()
    monkeypatch.setattr(execution_service, "_execute", fail_slack)
    first = asyncio.run(
        execute_mission({"session_factory": factory, "redis": redis}, mission_id)  # type: ignore[arg-type]
    )
    assert first == "partially_complete"

    async def read_steps() -> tuple[str, str, int, str | None, int]:
        async with factory() as session:
            steps = (
                (
                    await session.execute(
                        select(MissionStep).where(MissionStep.mission_id == uuid.UUID(mission_id))
                    )
                )
                .scalars()
                .all()
            )
            action_steps = [s for s in steps if s.sequence >= 10]
            jira_step = next(s for s in action_steps if s.name.startswith("jira."))
            slack_step = next(s for s in action_steps if s.name.startswith("slack."))
            return (
                jira_step.status,
                slack_step.status,
                slack_step.attempts,
                slack_step.last_error,
                jira_step.attempts,
            )

    jira_status, slack_status, slack_attempts, slack_error, jira_attempts_before = asyncio.run(
        read_steps()
    )
    assert jira_status == "verified"
    assert slack_status == "failed"
    assert slack_attempts >= 1
    assert slack_error is not None and "Slack" in slack_error

    # Resume through the real retry path: failed executions reset, mission
    # transitions back to RUNNING, and an execute_mission job is queued.
    retry = client.post(f"/api/missions/{mission_id}/retry", headers=headers)
    assert retry.status_code == 202

    monkeypatch.setattr(execution_service, "_execute", original_execute)
    second = asyncio.run(
        execute_mission({"session_factory": factory, "redis": FakeRedis()}, mission_id)  # type: ignore[arg-type]
    )
    assert second == "completed"

    async def read_final() -> tuple[str, int, str, int]:
        async with factory() as session:
            steps = (
                (
                    await session.execute(
                        select(MissionStep).where(MissionStep.mission_id == uuid.UUID(mission_id))
                    )
                )
                .scalars()
                .all()
            )
            action_steps = [s for s in steps if s.sequence >= 10]
            jira_step = next(s for s in action_steps if s.name.startswith("jira."))
            slack_step = next(s for s in action_steps if s.name.startswith("slack."))
            return (
                jira_step.status,
                jira_step.attempts,
                slack_step.status,
                slack_step.attempts,
            )

    jira_status, jira_attempts_after, slack_status, slack_attempts_after = asyncio.run(
        read_final()
    )
    assert jira_status == "verified"
    assert jira_attempts_after == jira_attempts_before
    assert slack_status == "verified"
    assert slack_attempts_after >= 1


def test_recovered_mission_can_be_claimed_and_completed(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = auth(client)
    mission_id = prepared_mission(client, headers)
    bundle = client.post(f"/api/missions/{mission_id}/approval", headers=headers).json()
    approved = client.post(
        f"/api/approvals/{bundle['id']}/approve", headers=headers, json={}
    )
    assert approved.status_code == 200
    factory = client.test_session_factory  # type: ignore[attr-defined]

    # Simulate a worker crash mid-execution: lease held by a dead worker.
    async def crash() -> None:
        async with factory() as session:
            mission = await session.get(Mission, uuid.UUID(mission_id))
            assert mission is not None
            mission.worker_id = "crashed-worker"
            mission.lease_expires_at = datetime.now(UTC) - timedelta(seconds=5)
            await session.commit()

    asyncio.run(crash())

    async def recover() -> list[uuid.UUID]:
        async with factory() as session:
            recovered = await recover_expired_missions(session)
            await session.commit()
            return recovered

    recovered = asyncio.run(recover())
    assert uuid.UUID(mission_id) in recovered

    # A new worker claims the recovered mission and completes it.
    second = asyncio.run(
        execute_mission({"session_factory": factory, "redis": FakeRedis()}, mission_id)  # type: ignore[arg-type]
    )
    assert second == "completed"

    async def assert_leased_then_released() -> None:
        async with factory() as session:
            mission = await session.get(Mission, uuid.UUID(mission_id))
            assert mission is not None
            assert mission.status == MissionStatus.COMPLETED
            assert mission.worker_id is None

    asyncio.run(assert_leased_then_released())
