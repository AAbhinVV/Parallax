"""Hermetic tests for the Parallax control-plane API.

Agent Core is simulated with httpx.MockTransport so tests never
require the Agent Core server or live credentials.
"""

from __future__ import annotations

import json
import uuid
from collections.abc import Iterator
from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient

from app.agent_client import AgentCoreClient
from app.main import app, get_agent_core_client


def make_client(
    handler: Any,
) -> TestClient:
    """Build a TestClient whose Agent Core client uses a mock transport."""

    def override() -> Iterator[AgentCoreClient]:
        yield AgentCoreClient(
            base_url="http://agent-core.test",
            transport=httpx.MockTransport(handler),
        )

    app.dependency_overrides[get_agent_core_client] = override
    return TestClient(app)


MISSION_ACK = {
    "missionId": "mission-1",
    "status": "waiting_for_approval",
    "currentStep": "approval_gate",
    "progress": 44,
    "approvalStatus": "pending",
    "policyRecommendation": {
        "recommendation": (
            "Create a Jira task for the payment retry work."
        ),
        "rationale": "Supported by the document.",
        "suggestedJiraSummary": "Implement payment retry",
        "suggestedJiraDescription": "Add retry handling to payments.",
    },
    "proposedActions": [
        {
            "id": "action-1",
            "type": "jira.create_issue",
            "target": "PAY",
            "reason": "Track follow-up work.",
            "requiresApproval": True,
            "status": "proposed",
        },
    ],
    "executionResults": [],
    "verificationResults": [],
    "slackSummary": "",
    "errors": [],
}

MISSION_STATE = {
    "missionId": "mission-1",
    "status": "waiting_for_approval",
    "currentStep": "approval_gate",
    "progress": 44,
    "approvalStatus": "pending",
    "policyRecommendation": None,
    "proposedActions": [],
    "executionResults": [],
    "verificationResults": [],
    "slackSummary": "",
    "errors": [],
}

DECISION_RESULT = {
    "missionId": "mission-1",
    "status": "completed",
    "currentStep": "audit_actions",
    "progress": 100,
    "approvalStatus": "approved",
    "policyRecommendation": None,
    "proposedActions": [],
    "executionResults": [],
    "verificationResults": [],
    "slackSummary": "",
    "errors": [],
}


def route_handler(request: httpx.Request) -> httpx.Response:
    if request.method == "POST" and request.url.path == "/missions":
        if b"unreachable" in request.content:
            return httpx.Response(500, json={"error": "boom"})

        payload = json.loads(request.content)
        ack = {
            **MISSION_ACK,
            "missionId": payload.get("missionId", "mission-1"),
        }
        return httpx.Response(202, json=ack)

    if request.method == "GET" and request.url.path == "/missions/mission-1":
        return httpx.Response(200, json=MISSION_STATE)

    if request.method == "GET" and request.url.path == "/missions/missing":
        return httpx.Response(404, json={"error": "Mission not found"})

    if (
        request.method == "POST"
        and request.url.path == "/missions/mission-1/approve"
    ):
        return httpx.Response(200, json=DECISION_RESULT)

    if (
        request.method == "POST"
        and request.url.path == "/missions/mission-1/reject"
    ):
        return httpx.Response(
            200,
            json={**DECISION_RESULT, "status": "rejected"},
        )

    return httpx.Response(404, json={"error": "Route not found"})


@pytest.fixture()
def api() -> TestClient:
    test_client = make_client(route_handler)
    yield test_client
    app.dependency_overrides.clear()


def test_health(api: TestClient) -> None:
    response = api.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert "agentCore" in body


def test_create_mission_generates_uuid_and_relays_ack(
    api: TestClient,
) -> None:
    response = api.post(
        "/api/v1/missions",
        json={"mission": "Review PR 142 in payments-service"},
    )

    assert response.status_code == 202
    body = response.json()

    # The backend owns the mission ID.
    uuid.UUID(body["missionId"])

    assert body["status"] == "waiting_for_approval"
    assert body["currentStep"] == "approval_gate"
    assert body["progress"] == 44
    assert body["approvalStatus"] == "pending"
    assert (
        body["policyRecommendation"]["suggestedJiraSummary"]
        == "Implement payment retry"
    )
    assert body["errors"] == []


def test_create_mission_requires_mission_text(api: TestClient) -> None:
    response = api.post("/api/v1/missions", json={})

    assert response.status_code == 422


def test_get_mission(api: TestClient) -> None:
    response = api.get("/api/v1/missions/mission-1")

    assert response.status_code == 200
    body = response.json()
    assert body["missionId"] == "mission-1"
    assert body["currentStep"] == "approval_gate"
    assert body["progress"] == 44


def test_get_missing_mission_maps_to_404(api: TestClient) -> None:
    response = api.get("/api/v1/missions/missing")

    assert response.status_code == 404


def test_approve_mission(api: TestClient) -> None:
    response = api.post("/api/v1/missions/mission-1/approve")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "completed"
    assert body["progress"] == 100
    assert body["currentStep"] == "audit_actions"


def test_reject_mission(api: TestClient) -> None:
    response = api.post("/api/v1/missions/mission-1/reject")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "rejected"
    assert body["missionId"] == "mission-1"


def test_agent_core_failure_maps_to_502(api: TestClient) -> None:
    response = api.post(
        "/api/v1/missions",
        json={"mission": "unreachable"},
    )

    assert response.status_code == 502
