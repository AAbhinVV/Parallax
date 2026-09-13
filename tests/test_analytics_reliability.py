import uuid
from datetime import UTC, datetime
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.integrations.contracts import AdapterError, ApprovedWriteContext
from app.integrations.mock import MockJiraAdapter
from scripts.backup_local import pg_dump_url

OWNER = {
    "email": "analytics-owner@example.com",
    "password": "correct-horse-battery-staple",
    "display_name": "Analytics Owner",
    "workspace_name": "Analytics Workspace",
    "workspace_slug": "analytics-workspace",
}


def register(client: TestClient, payload: dict[str, Any] = OWNER) -> dict[str, str]:
    response = client.post("/api/auth/register", json=payload)
    assert response.status_code == 201
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_timeline_audit_sla_analytics_health_and_trace_contract(client: TestClient) -> None:
    headers = register(client)
    created = client.post(
        "/api/missions",
        json={"prompt": "Exercise Phase 8 analytics", "project": "General"},
        headers=headers,
    )
    assert created.status_code == 202
    assert created.headers["X-Trace-ID"] == created.headers["X-Correlation-ID"]
    mission_id = created.json()["id"]

    timeline = client.get(f"/api/missions/{mission_id}/timeline", headers=headers)
    assert timeline.status_code == 200
    assert timeline.json()[0]["to_status"] == "queued"
    assert timeline.json()[0]["detail"] == "Manual mission submitted"

    audit = client.get(f"/api/audit-events?mission_id={mission_id}", headers=headers)
    assert audit.status_code == 200
    assert audit.json()[0]["event_type"] == "mission.created"
    uuid.UUID(audit.json()[0]["correlation_id"])

    sla = client.get(f"/api/missions/{mission_id}/sla", headers=headers).json()
    assert sla["mission_id"] == mission_id
    assert sla["target_seconds"] == 3600
    assert sla["breached"] is False

    overview = client.get("/api/analytics/overview", headers=headers)
    assert overview.status_code == 200
    assert overview.json()["total_missions"] == 1
    assert overview.json()["completion_rate_pct"] == 0
    assert {item["provider"] for item in overview.json()["executions_by_provider"]} == {
        "github",
        "jira",
        "notion",
        "slack",
    }

    health = client.get("/api/integrations/health", headers=headers)
    assert health.status_code == 200
    assert {item["name"] for item in health.json()} == {"GitHub", "Jira", "Notion", "Slack"}
    assert all(item["mode"] == "mock" for item in health.json())


def test_phase_eight_reads_are_workspace_scoped(client: TestClient) -> None:
    first = register(client)
    mission_id = client.post(
        "/api/missions",
        json={"prompt": "Private analytics mission", "project": "General"},
        headers=first,
    ).json()["id"]
    second_owner = dict(OWNER)
    second_owner.update(
        email="analytics-other@example.com",
        workspace_name="Analytics Other",
        workspace_slug="analytics-other",
    )
    second = register(client, second_owner)
    assert client.get(f"/api/missions/{mission_id}/timeline", headers=second).status_code == 404
    assert client.get(f"/api/missions/{mission_id}/sla", headers=second).status_code == 404
    assert client.get("/api/audit-events", headers=second).json() == []
    assert client.get("/api/analytics/overview", headers=second).json()["total_missions"] == 0


def test_backup_url_removes_async_driver() -> None:
    assert (
        pg_dump_url("postgresql+asyncpg://user:pass@localhost:5432/parallax")
        == "postgresql://user:pass@localhost:5432/parallax"
    )


@pytest.mark.asyncio
async def test_local_failure_injection_is_deterministic(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "demo_failure_provider", "jira")
    adapter = MockJiraAdapter()
    with pytest.raises(AdapterError, match="Injected local demo failure"):
        await adapter.create_issue(
            {"summary": "Expected failure"},
            ApprovedWriteContext(
                approval_id=uuid.uuid4(),
                mission_id=uuid.uuid4(),
                approved_at=datetime.now(UTC),
            ),
        )
