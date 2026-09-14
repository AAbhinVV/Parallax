"""K3: task identity, completion proofs, duplicate/resume resolution."""

from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime

from fastapi.testclient import TestClient
from sqlalchemy import func, select

from parallax_backend.models import (
    ActionProposal,
    ExecutionRecord,
    IntegrationProvider,
    Mission,
    MissionCompletionProof,
    MissionStatus,
    Project,
    User,
    VerificationRecord,
    Workspace,
)
from parallax_backend.services.completion import build_completion_proof
from parallax_backend.services.resolution import resolve_existing_objective
from parallax_backend.services.task_identity import task_fingerprint


async def _make_workspace(session) -> tuple[Workspace, User, Project]:
    workspace = Workspace(name="K3 Workspace", slug=f"k3-{uuid.uuid4().hex[:8]}")
    user = User(
        email=f"k3-{uuid.uuid4().hex[:8]}@example.com",
        password_hash="x",
        display_name="K3 Tester",
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
    prompt: str,
    status: MissionStatus = MissionStatus.QUEUED,
) -> Mission:
    mission = Mission(
        workspace_id=workspace.id,
        created_by_user_id=user.id,
        project_id=project.id,
        prompt=prompt,
        project_name=project.name,
        status=status,
        correlation_id=uuid.uuid4(),
        task_fingerprint=task_fingerprint(prompt),
    )
    session.add(mission)
    await session.flush()
    return mission


def test_fingerprint_is_stable_under_normalization() -> None:
    first = "Create the Jira task and notify the team."
    second = "  create   the JIRA TASK   and notify the team.  "

    assert task_fingerprint(first) == task_fingerprint(second)
    assert task_fingerprint(first) != task_fingerprint("Update the Jira issue")
    assert len(task_fingerprint(first)) == 64


def test_resolution_is_new_without_prior_mission(client) -> None:
    factory = client.test_session_factory

    async def scenario() -> None:
        async with factory() as session:
            workspace, user, project = await _make_workspace(session)

            resolution = await resolve_existing_objective(
                session, workspace.id, project.id, "Synchronize the payment release."
            )

            assert resolution.decision == "new"
            assert resolution.prior_mission is None
            assert resolution.proof is None

    asyncio.run(scenario())


def test_resolution_resume_for_incomplete_prior_mission(client) -> None:
    factory = client.test_session_factory
    prompt = "Synchronize the payment release."

    async def scenario() -> None:
        async with factory() as session:
            workspace, user, project = await _make_workspace(session)
            await _make_mission(session, workspace, user, project, prompt)

            resolution = await resolve_existing_objective(
                session, workspace.id, project.id, prompt.upper()
            )

            assert resolution.decision == "resume"
            assert resolution.prior_mission is not None
            assert resolution.proof is None

    asyncio.run(scenario())


def test_resolution_completed_requires_verified_proof(client) -> None:
    factory = client.test_session_factory
    prompt = "Synchronize the payment release."

    async def scenario() -> None:
        async with factory() as session:
            workspace, user, project = await _make_workspace(session)
            prior = await _make_mission(
                session, workspace, user, project, prompt, status=MissionStatus.COMPLETED
            )

            # Completed without a proof: memory without evidence is not truth.
            unverified = await resolve_existing_objective(session, workspace.id, project.id, prompt)
            assert unverified.decision == "resume"

            proof = MissionCompletionProof(
                workspace_id=workspace.id,
                mission_id=prior.id,
                status="verified",
                actions=[
                    {
                        "provider": "jira",
                        "operation": "issue.update",
                        "external_id": "PAY-18",
                        "verified": True,
                        "verification_id": None,
                    }
                ],
                verification_ids=[],
                completed_at=datetime.now(UTC),
            )
            session.add(proof)
            await session.flush()

            verified = await resolve_existing_objective(session, workspace.id, project.id, prompt)
            assert verified.decision == "completed"
            assert verified.prior_mission is not None
            assert verified.prior_mission.id == prior.id
            assert verified.proof is not None

    asyncio.run(scenario())


def test_resolution_scopes_to_project(client) -> None:
    factory = client.test_session_factory
    prompt = "Synchronize the payment release."

    async def scenario() -> None:
        async with factory() as session:
            workspace, user, project = await _make_workspace(session)
            other_project = Project(workspace_id=workspace.id, name="Platform")
            session.add(other_project)
            await session.flush()
            await _make_mission(
                session, workspace, user, project, prompt, status=MissionStatus.COMPLETED
            )

            resolution = await resolve_existing_objective(
                session, workspace.id, other_project.id, prompt
            )

            assert resolution.decision == "new"

    asyncio.run(scenario())


def test_completion_proof_built_from_verified_executions(client) -> None:
    factory = client.test_session_factory

    async def scenario() -> None:
        async with factory() as session:
            workspace, user, project = await _make_workspace(session)
            mission = await _make_mission(
                session, workspace, user, project, "Handle the payment release."
            )
            proposal = ActionProposal(
                workspace_id=workspace.id,
                mission_id=mission.id,
                approval_bundle_id=uuid.uuid4(),
                sequence=1,
                provider=IntegrationProvider.JIRA,
                operation="issue.update",
                rationale="Sync status",
                payload={},
                citations=[],
            )
            session.add(proposal)
            await session.flush()
            execution = ExecutionRecord(
                workspace_id=workspace.id,
                mission_id=mission.id,
                action_proposal_id=proposal.id,
                idempotency_key=f"action:{proposal.id}",
                status="verified",
                external_id="PAY-18",
            )
            session.add(execution)
            await session.flush()
            verification = VerificationRecord(
                workspace_id=workspace.id,
                mission_id=mission.id,
                execution_id=execution.id,
                status="verified",
                evidence={"external_id": "PAY-18"},
                checked_at=datetime.now(UTC),
            )
            session.add(verification)
            await session.flush()

            proof = await build_completion_proof(session, mission)
            assert proof is not None
            assert proof.actions == [
                {
                    "provider": "jira",
                    "operation": "issue.update",
                    "external_id": "PAY-18",
                    "verified": True,
                    "verification_id": str(verification.id),
                }
            ]
            assert proof.verification_ids == [str(verification.id)]

            # Re-completion refreshes the proof instead of duplicating rows.
            refreshed = await build_completion_proof(session, mission)
            assert refreshed is not None
            assert refreshed.id == proof.id

            count = (
                await session.execute(
                    select(func.count())
                    .select_from(MissionCompletionProof)
                    .where(MissionCompletionProof.mission_id == mission.id)
                )
            ).scalar_one()
            assert count == 1

    asyncio.run(scenario())


def test_create_mission_stores_fingerprint(client: TestClient) -> None:
    from tests.test_missions import headers, register

    token = str(register(client)["access_token"])
    created = client.post(
        "/api/missions",
        json={"prompt": "Prepare the quarterly compliance review", "project": "General"},
        headers=headers(token),
    )
    assert created.status_code == 202
    mission_id = created.json()["id"]

    factory = client.test_session_factory

    async def load() -> str | None:
        async with factory() as session:
            mission = await session.get(Mission, uuid.UUID(mission_id))
            assert mission is not None
            return mission.task_fingerprint

    fingerprint = asyncio.run(load())
    assert fingerprint == task_fingerprint("Prepare the quarterly compliance review")


def test_create_mission_recognizes_completed_duplicate(client: TestClient) -> None:
    from tests.test_missions import headers, register

    token = str(register(client)["access_token"])
    prompt = "Synchronize the payment release with tracking"
    first = client.post(
        "/api/missions",
        json={"prompt": prompt, "project": "General"},
        headers=headers(token),
    )
    assert first.status_code == 202
    prior_id = first.json()["id"]

    factory = client.test_session_factory

    async def complete_prior() -> None:
        async with factory() as session:
            mission = await session.get(Mission, uuid.UUID(prior_id))
            assert mission is not None
            mission.status = MissionStatus.COMPLETED
            session.add(
                MissionCompletionProof(
                    workspace_id=mission.workspace_id,
                    mission_id=mission.id,
                    status="verified",
                    actions=[
                        {
                            "provider": "jira",
                            "operation": "issue.update",
                            "external_id": "PAY-18",
                            "verified": True,
                            "verification_id": None,
                        }
                    ],
                    verification_ids=[],
                    completed_at=datetime.now(UTC),
                )
            )
            await session.commit()

    asyncio.run(complete_prior())

    replay = client.post(
        "/api/missions",
        json={"prompt": "synchronize the PAYMENT release with tracking", "project": "General"},
        headers=headers(token),
    )
    assert replay.status_code == 202
    assert replay.json()["id"] == prior_id
    assert replay.json()["status"] == "completed"

    async def count_missions() -> int:
        async with factory() as session:
            return (
                await session.execute(
                    select(func.count())
                    .select_from(Mission)
                    .where(Mission.task_fingerprint == task_fingerprint(prompt))
                )
            ).scalar_one()

    assert asyncio.run(count_missions()) == 1
