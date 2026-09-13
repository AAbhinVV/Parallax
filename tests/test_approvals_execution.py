import asyncio
import uuid
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from parallax_backend.integrations.contracts import AdapterError
from parallax_backend.models import (
    ExecutionRecord,
    IntegrationProvider,
    Mission,
    MissionStatus,
    VerificationRecord,
)
from parallax_backend.services import execution as execution_service
from parallax_backend.services.execution import execute_mission
from parallax_backend.worker import prepare_mission

OWNER = {
    "email": "approval-owner@example.com",
    "password": "correct-horse-battery-staple",
    "display_name": "Approval Owner",
    "workspace_name": "Approval Workspace",
    "workspace_slug": "approval-workspace",
}


def auth(client: TestClient) -> dict[str, str]:
    response = client.post("/api/auth/register", json=OWNER)
    assert response.status_code == 201
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def prepared_mission(client: TestClient, headers: dict[str, str]) -> str:
    mission_id = client.post(
        "/api/missions",
        json={"prompt": "Review the payment migration", "project": "General"},
        headers=headers,
    ).json()["id"]
    factory = client.test_session_factory  # type: ignore[attr-defined]
    assert (
        asyncio.run(prepare_mission({"session_factory": factory}, mission_id))
        == "context_collected"
    )
    return str(mission_id)


def test_policy_approval_edit_reject_and_terminal_guard(client: TestClient) -> None:
    headers = auth(client)
    mission_id = prepared_mission(client, headers)
    created = client.post(f"/api/missions/{mission_id}/approval", headers=headers)
    assert created.status_code == 201
    bundle = created.json()
    assert bundle["status"] == "pending"
    assert bundle["policy"]["allowed"] is True
    assert bundle["policy"]["approval_required"] is True

    bad_edit = client.post(
        f"/api/approvals/{bundle['id']}/edit",
        headers=headers,
        json={
            "actions": [
                {
                    "provider": "github",
                    "operation": "repository.delete",
                    "rationale": "This must never pass",
                    "payload": {},
                    "citations": [bundle["actions"][0]["citations"][0]],
                }
            ]
        },
    )
    assert bad_edit.status_code == 422

    edited_actions = bundle["actions"][:1]
    for action in edited_actions:
        for key in ("id", "sequence", "status"):
            action.pop(key)
    edited = client.post(
        f"/api/approvals/{bundle['id']}/edit",
        headers=headers,
        json={"actions": edited_actions, "note": "Reduced scope"},
    )
    assert edited.status_code == 201
    assert edited.json()["version"] == 2
    rejected = client.post(
        f"/api/approvals/{edited.json()['id']}/reject",
        headers=headers,
        json={"note": "Not this release"},
    )
    assert rejected.status_code == 200
    assert rejected.json()["status"] == "rejected"
    assert (
        client.post(
            f"/api/approvals/{edited.json()['id']}/approve", headers=headers, json={}
        ).status_code
        == 409
    )
    assert client.get(f"/api/missions/{mission_id}", headers=headers).json()["status"] == "rejected"


def test_approved_actions_execute_verify_and_are_idempotent(client: TestClient) -> None:
    headers = auth(client)
    mission_id = prepared_mission(client, headers)
    bundle = client.post(f"/api/missions/{mission_id}/approval", headers=headers).json()
    approved = client.post(
        f"/api/approvals/{bundle['id']}/approve",
        headers=headers,
        json={"note": "Approved for execution"},
    )
    assert approved.status_code == 200
    assert client.get(f"/api/missions/{mission_id}", headers=headers).json()["status"] == "running"
    factory = client.test_session_factory  # type: ignore[attr-defined]

    class FakeRedis:
        def __init__(self) -> None:
            self.locked = False

        async def set(self, *_: object, **__: object) -> bool:
            if self.locked:
                return False
            self.locked = True
            return True

        async def eval(self, *_: object) -> int:
            self.locked = False
            return 1

    redis = FakeRedis()

    async def run_twice() -> tuple[str, str, int, int, MissionStatus]:
        first = await execute_mission(
            {"session_factory": factory, "redis": redis},
            mission_id,  # type: ignore[arg-type]
        )
        second = await execute_mission(
            {"session_factory": factory, "redis": redis},
            mission_id,  # type: ignore[arg-type]
        )
        async with factory() as session:
            executions = int(
                await session.scalar(select(func.count()).select_from(ExecutionRecord)) or 0
            )
            verifications = int(
                await session.scalar(select(func.count()).select_from(VerificationRecord)) or 0
            )
            mission = (
                await session.execute(select(Mission).where(Mission.id == uuid.UUID(mission_id)))
            ).scalar_one()
            return first, second, executions, verifications, mission.status

    first, second, execution_count, verification_count, mission_status = asyncio.run(run_twice())
    assert first == "completed"
    assert second == "completed"
    assert execution_count == len(bundle["actions"])
    assert verification_count == len(bundle["actions"])
    assert mission_status == MissionStatus.COMPLETED
    records = client.get(f"/api/missions/{mission_id}/executions", headers=headers)
    assert records.status_code == 200
    assert all(item["status"] == "verified" for item in records.json())
    assert all(item["verification"]["status"] == "verified" for item in records.json())


def test_partial_failure_can_retry_without_repeating_verified_actions(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = auth(client)
    mission_id = prepared_mission(client, headers)
    bundle = client.post(f"/api/missions/{mission_id}/approval", headers=headers).json()
    client.post(f"/api/approvals/{bundle['id']}/approve", headers=headers, json={})
    factory = client.test_session_factory  # type: ignore[attr-defined]
    original_execute = execution_service._execute

    async def fail_slack(action: Any, approval: Any) -> Any:
        if action.provider == IntegrationProvider.SLACK:
            raise AdapterError(IntegrationProvider.SLACK, "Temporary Slack error", retryable=True)
        return await original_execute(action, approval)

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

    redis = FakeRedis()
    monkeypatch.setattr(execution_service, "_execute", fail_slack)
    first = asyncio.run(
        execute_mission(
            {"session_factory": factory, "redis": redis},  # type: ignore[arg-type]
            mission_id,
        )
    )
    assert first == "partially_complete"
    records = client.get(f"/api/missions/{mission_id}/executions", headers=headers).json()
    assert {item["status"] for item in records} == {"verified", "failed"}
    verified_id = next(item["id"] for item in records if item["status"] == "verified")

    retry = client.post(f"/api/missions/{mission_id}/retry", headers=headers)
    assert retry.status_code == 202
    monkeypatch.setattr(execution_service, "_execute", original_execute)
    assert (
        asyncio.run(
            execute_mission(
                {"session_factory": factory, "redis": redis},  # type: ignore[arg-type]
                mission_id,
            )
        )
        == "completed"
    )
    final_records = client.get(f"/api/missions/{mission_id}/executions", headers=headers).json()
    assert all(item["status"] == "verified" for item in final_records)
    assert any(item["id"] == verified_id for item in final_records)
