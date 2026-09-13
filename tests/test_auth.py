import asyncio
import uuid

from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.models import Integration, User, WorkspaceMembership, WorkspaceRole
from app.security import hash_password

OWNER = {
    "email": "owner@example.com",
    "password": "correct-horse-battery-staple",
    "display_name": "Owner",
    "workspace_name": "Example Engineering",
    "workspace_slug": "example-engineering",
}


def register(client: TestClient) -> dict[str, object]:
    response = client.post("/api/auth/register", json=OWNER)
    assert response.status_code == 201
    return response.json()


def auth_header(token: object) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_registration_login_and_me(client: TestClient) -> None:
    tokens = register(client)
    me = client.get("/api/auth/me", headers=auth_header(tokens["access_token"]))
    assert me.status_code == 200
    assert me.json()["user"]["email"] == OWNER["email"]
    assert me.json()["current_workspace"]["role"] == "owner"
    assert "password_hash" not in me.text

    login = client.post(
        "/api/auth/login", json={"email": OWNER["email"], "password": OWNER["password"]}
    )
    assert login.status_code == 200
    assert login.json()["workspace_id"] == tokens["workspace_id"]

    factory = client.test_session_factory  # type: ignore[attr-defined]

    async def integration_count() -> int:
        async with factory() as session:
            return int(await session.scalar(select(func.count()).select_from(Integration)) or 0)

    assert asyncio.run(integration_count()) == 4


def test_duplicate_registration_and_bad_login(client: TestClient) -> None:
    register(client)
    duplicate = client.post("/api/auth/register", json=OWNER)
    assert duplicate.status_code == 409

    bad_login = client.post(
        "/api/auth/login", json={"email": OWNER["email"], "password": "wrong-password"}
    )
    assert bad_login.status_code == 401


def test_refresh_rotation_and_logout_revoke_sessions(client: TestClient) -> None:
    original = register(client)
    rotated = client.post("/api/auth/refresh", json={"refresh_token": original["refresh_token"]})
    assert rotated.status_code == 200

    reused = client.post("/api/auth/refresh", json={"refresh_token": original["refresh_token"]})
    assert reused.status_code == 401
    old_access = client.get("/api/auth/me", headers=auth_header(original["access_token"]))
    assert old_access.status_code == 401

    logout = client.post(
        "/api/auth/logout", json={"refresh_token": rotated.json()["refresh_token"]}
    )
    assert logout.status_code == 204
    after_logout = client.get("/api/auth/me", headers=auth_header(rotated.json()["access_token"]))
    assert after_logout.status_code == 401


def test_workspace_header_cannot_escape_token_scope(client: TestClient) -> None:
    tokens = register(client)
    headers = auth_header(tokens["access_token"])
    headers["X-Workspace-ID"] = "b7b8ce2f-7af7-4515-b83c-f43aa9d40a23"
    response = client.get("/api/workspaces/current", headers=headers)
    assert response.status_code == 403


def test_viewer_cannot_change_roles(client: TestClient) -> None:
    owner_tokens = register(client)
    workspace_id = uuid.UUID(str(owner_tokens["workspace_id"]))
    factory = client.test_session_factory  # type: ignore[attr-defined]

    async def create_viewer() -> None:
        async with factory() as session:
            viewer = User(
                email="viewer@example.com",
                display_name="Viewer",
                password_hash=hash_password("viewer-password-secure"),
            )
            session.add(viewer)
            await session.flush()
            session.add(
                WorkspaceMembership(
                    workspace_id=workspace_id,
                    user_id=viewer.id,
                    role=WorkspaceRole.VIEWER,
                )
            )
            await session.commit()

    asyncio.run(create_viewer())
    login = client.post(
        "/api/auth/login",
        json={
            "email": "viewer@example.com",
            "password": "viewer-password-secure",
            "workspace_id": str(workspace_id),
        },
    )
    assert login.status_code == 200
    members = client.get(
        "/api/workspaces/current/members", headers=auth_header(login.json()["access_token"])
    )
    owner_id = next(item["user_id"] for item in members.json() if item["role"] == "owner")
    change = client.patch(
        f"/api/workspaces/current/members/{owner_id}",
        json={"role": "viewer"},
        headers=auth_header(login.json()["access_token"]),
    )
    assert change.status_code == 403


def test_workspace_must_keep_an_owner(client: TestClient) -> None:
    tokens = register(client)
    headers = auth_header(tokens["access_token"])
    members = client.get("/api/workspaces/current/members", headers=headers)
    owner_id = members.json()[0]["user_id"]
    response = client.patch(
        f"/api/workspaces/current/members/{owner_id}",
        json={"role": "admin"},
        headers=headers,
    )
    assert response.status_code == 409
