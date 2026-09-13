import asyncio
import uuid
from typing import Any

from fastapi.testclient import TestClient
from sqlalchemy import func, select

from parallax_backend.models import (
    AgentAssessment,
    AuditEvent,
    ContextPack,
    Mission,
    MissionStatus,
    MissionStep,
    OutboxJob,
)
from parallax_backend.worker import dispatch_outbox, prepare_mission

OWNER = {
    "email": "mission-owner@example.com",
    "password": "correct-horse-battery-staple",
    "display_name": "Mission Owner",
    "workspace_name": "Mission Workspace",
    "workspace_slug": "mission-workspace",
}


def register(client: TestClient) -> dict[str, Any]:
    response = client.post("/api/auth/register", json=OWNER)
    assert response.status_code == 201
    return response.json()


def headers(token: str, key: str | None = None) -> dict[str, str]:
    result = {"Authorization": f"Bearer {token}"}
    if key:
        result["Idempotency-Key"] = key
    return result


def test_mission_lifecycle_and_dashboard_contract(client: TestClient) -> None:
    token = str(register(client)["access_token"])
    payload = {"prompt": "Prepare the release readiness plan", "project": "General"}
    created = client.post("/api/missions", json=payload, headers=headers(token, "mission-1"))
    assert created.status_code == 202
    mission = created.json()
    uuid.UUID(mission["id"])
    assert mission["status"] == "queued"
    assert mission["steps"] == []

    replay = client.post("/api/missions", json=payload, headers=headers(token, "mission-1"))
    assert replay.status_code == 202
    assert replay.json()["id"] == mission["id"]
    conflict = client.post(
        "/api/missions",
        json={"prompt": "A different request", "project": "General"},
        headers=headers(token, "mission-1"),
    )
    assert conflict.status_code == 409

    detail = client.get(f"/api/missions/{mission['id']}", headers=headers(token))
    assert detail.status_code == 200
    assert len(client.get("/api/missions?limit=1&offset=0", headers=headers(token)).json()) == 1
    assert client.get("/api/dashboard/stats", headers=headers(token)).json()["active_tasks"] == 1
    assert (
        client.get("/api/dashboard/activity", headers=headers(token)).json()[0]["title"]
        == "Mission queued"
    )
    assert (
        client.get("/api/dashboard/projects", headers=headers(token)).json()[0]["name"] == "General"
    )
    integrations = client.get("/api/integrations", headers=headers(token)).json()
    assert {item["name"] for item in integrations} == {"GitHub", "Jira", "Notion", "Slack"}

    factory = client.test_session_factory  # type: ignore[attr-defined]

    async def persisted_counts() -> tuple[int, int]:
        async with factory() as session:
            outbox = int(await session.scalar(select(func.count()).select_from(OutboxJob)) or 0)
            audit = int(await session.scalar(select(func.count()).select_from(AuditEvent)) or 0)
            return outbox, audit

    assert asyncio.run(persisted_counts()) == (1, 1)

    cancelled = client.post(f"/api/missions/{mission['id']}/cancel", headers=headers(token))
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "cancelled"
    assert (
        client.post(f"/api/missions/{mission['id']}/cancel", headers=headers(token)).status_code
        == 409
    )


def test_mission_validation_and_workspace_isolation(client: TestClient) -> None:
    first = register(client)
    token = str(first["access_token"])
    missing_project = client.post(
        "/api/missions",
        json={"prompt": "Plan something", "project": "Unknown"},
        headers=headers(token),
    )
    assert missing_project.status_code == 422
    created = client.post(
        "/api/missions",
        json={"prompt": "Private workspace plan", "project": "General"},
        headers=headers(token),
    ).json()

    second_payload = dict(OWNER)
    second_payload.update(
        email="other-owner@example.com",
        workspace_name="Other Workspace",
        workspace_slug="other-workspace",
    )
    second = client.post("/api/auth/register", json=second_payload)
    assert second.status_code == 201
    other_headers = headers(str(second.json()["access_token"]))
    assert client.get(f"/api/missions/{created['id']}", headers=other_headers).status_code == 404
    assert client.get("/api/missions", headers=other_headers).json() == []


def test_outbox_dispatch_and_worker_context_agent_pipeline(client: TestClient) -> None:
    token = str(register(client)["access_token"])
    mission_id = client.post(
        "/api/missions",
        json={"prompt": "Build a context pack", "project": "General"},
        headers=headers(token),
    ).json()["id"]
    factory = client.test_session_factory  # type: ignore[attr-defined]

    class FakeRedis:
        def __init__(self) -> None:
            self.calls: list[tuple[object, ...]] = []

        async def enqueue_job(self, *args: object, **kwargs: object) -> None:
            self.calls.append((*args, kwargs))

    fake_redis = FakeRedis()

    async def run_worker() -> tuple[int, str, MissionStatus, int, int, int]:
        dispatched = await dispatch_outbox({"session_factory": factory, "redis": fake_redis})  # type: ignore[arg-type]
        result = await prepare_mission({"session_factory": factory}, mission_id)
        async with factory() as session:
            mission = (
                await session.execute(select(Mission).where(Mission.id == uuid.UUID(mission_id)))
            ).scalar_one()
            step_count = int(
                await session.scalar(
                    select(func.count())
                    .select_from(MissionStep)
                    .where(MissionStep.mission_id == uuid.UUID(mission_id))
                )
                or 0
            )
            context_count = int(
                await session.scalar(
                    select(func.count())
                    .select_from(ContextPack)
                    .where(ContextPack.mission_id == uuid.UUID(mission_id))
                )
                or 0
            )
            assessment_count = int(
                await session.scalar(
                    select(func.count())
                    .select_from(AgentAssessment)
                    .where(AgentAssessment.mission_id == uuid.UUID(mission_id))
                )
                or 0
            )
            return (
                dispatched,
                result,
                mission.status,
                step_count,
                context_count,
                assessment_count,
            )

    dispatched, result, status, step_count, context_count, assessment_count = asyncio.run(
        run_worker()
    )
    assert dispatched == 1
    assert fake_redis.calls[0][0:2] == ("prepare_mission", mission_id)
    assert result == "context_collected"
    assert status == MissionStatus.CONTEXT_COLLECTED
    assert step_count == 3
    assert context_count == 1
    assert assessment_count == 1

    context_response = client.get(
        f"/api/missions/{mission_id}/context-pack", headers=headers(token)
    )
    assert context_response.status_code == 200
    assert len(context_response.json()["evidence"]) == 3
    assessment_response = client.get(
        f"/api/missions/{mission_id}/assessment", headers=headers(token)
    )
    assert assessment_response.status_code == 200
    assessment = assessment_response.json()
    assert assessment["mode"] == "fallback"
    assert assessment["risk_level"] in {"low", "medium", "high", "critical"}
    evidence_keys = {item["key"] for item in context_response.json()["evidence"]}
    assert set(assessment["citations"]) <= evidence_keys
