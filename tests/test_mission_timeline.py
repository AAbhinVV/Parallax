"""Mission timeline: merged transitions, knowledge, executions, verifications, approvals."""

from __future__ import annotations

import asyncio

from fastapi.testclient import TestClient

from app.services.execution import execute_mission
from app.worker import prepare_mission

OWNER = {
    "email": "timeline-owner@example.com",
    "password": "correct-horse-battery-staple",
    "display_name": "Timeline Owner",
    "workspace_name": "Timeline Workspace",
    "workspace_slug": "timeline-workspace",
}


def auth(client: TestClient) -> dict[str, str]:
    response = client.post("/api/auth/register", json=OWNER)
    assert response.status_code == 201
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


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


def test_timeline_merges_all_mission_events(client: TestClient) -> None:
    headers = auth(client)
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
    bundle = client.post(f"/api/missions/{mission_id}/approval", headers=headers).json()
    client.post(f"/api/approvals/{bundle['id']}/approve", headers=headers, json={})
    assert (
        asyncio.run(
            execute_mission({"session_factory": factory, "redis": FakeRedis()}, mission_id)
        )
        == "completed"
    )

    timeline = client.get(f"/api/missions/{mission_id}/timeline", headers=headers)
    assert timeline.status_code == 200
    events = timeline.json()
    types = [event["event_type"] for event in events]

    assert events[0]["event_type"] == "mission.transition"
    assert events[0]["to_status"] == "queued"
    assert events[0]["detail"] == "Manual mission submitted"
    assert "knowledge.fact" in types
    assert "approval.bundle" in types
    assert "execution" in types
    assert "verification" in types

    # Chronological order with deterministic type tiebreak.
    created = [event["created_at"] for event in events]
    assert created == sorted(created)

    execution_events = [event for event in events if event["event_type"] == "execution"]
    assert execution_events
    assert all("attempts" in event["detail"] for event in execution_events)

    verification_events = [event for event in events if event["event_type"] == "verification"]
    assert all(event["title"].startswith("Verification") for event in verification_events)

    knowledge_events = [event for event in events if event["event_type"] == "knowledge.fact"]
    assert knowledge_events
    assert all(" · " in event["title"] for event in knowledge_events)

    approval_events = [event for event in events if event["event_type"] == "approval.bundle"]
    assert approval_events
    assert approval_events[-1]["title"] == "Approval bundle approved"


def test_timeline_only_includes_own_mission_events(client: TestClient) -> None:
    headers = auth(client)
    first_mission = client.post(
        "/api/missions",
        json={"prompt": "First mission", "project": "General"},
        headers=headers,
    ).json()["id"]
    second_mission = client.post(
        "/api/missions",
        json={"prompt": "Second mission", "project": "General"},
        headers=headers,
    ).json()["id"]

    first_timeline = client.get(f"/api/missions/{first_mission}/timeline", headers=headers).json()
    second_timeline = client.get(
        f"/api/missions/{second_mission}/timeline", headers=headers
    ).json()
    assert len(first_timeline) == 1
    assert len(second_timeline) == 1
    assert first_timeline[0]["id"] != second_timeline[0]["id"]
