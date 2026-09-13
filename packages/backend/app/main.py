"""Parallax FastAPI control-plane.

Responsibilities (per project architecture):
- API routes and request validation
- Forwarding natural-language missions to Agent Core (:4010)
- Relaying mission state, approvals and audit info to callers

Mission planning, approval gating, authorized execution,
verification and auditability live in Agent Core (LangGraph),
NOT here.
"""

from __future__ import annotations

from typing import Any, AsyncIterator
from uuid import uuid4

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from .agent_client import AgentCoreClient, AgentCoreError
from .config import AGENT_CORE_URL

app = FastAPI(
    title="Parallax Backend",
    description=(
        "Control-plane API. Missions are planned, approved, executed, "
        "verified and audited by Agent Core."
    ),
    version="0.1.0",
)


async def get_agent_core_client() -> AsyncIterator[AgentCoreClient]:
    client = AgentCoreClient()
    try:
        yield client
    finally:
        await client.aclose()


# --------------------------------------------------------------------------
# Schemas
# --------------------------------------------------------------------------


class MissionRequest(BaseModel):
    mission: str = Field(min_length=1, description="Natural-language mission.")
    missionId: str | None = Field(
        default=None,
        description="Optional client-supplied mission identifier.",
    )


class MissionAck(BaseModel):
    """Normalized mission response relayed from Agent Core."""

    missionId: str
    status: str
    currentStep: str | None = None
    progress: int = 0
    approvalStatus: str = "not_required"
    policyRecommendation: Any = None
    proposedActions: list[Any] = Field(default_factory=list)
    executionResults: list[Any] = Field(default_factory=list)
    verificationResults: list[Any] = Field(default_factory=list)
    slackSummary: str = ""
    errors: list[str] = Field(default_factory=list)


# --------------------------------------------------------------------------
# Routes
# --------------------------------------------------------------------------


@app.get("/health")
async def health() -> dict[str, str]:
    return {
        "status": "ok",
        "agentCore": AGENT_CORE_URL,
    }


@app.post(
    "/api/v1/missions",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=MissionAck,
)
async def create_mission(
    request: MissionRequest,
    client: AgentCoreClient = Depends(get_agent_core_client),
) -> Any:
    """Start a mission. The backend owns the mission ID (uuid4)."""
    mission_id = str(uuid4())

    try:
        return await client.create_mission(
            mission=request.mission,
            mission_id=mission_id,
        )
    except AgentCoreError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc


@app.get("/api/v1/missions/{mission_id}")
async def get_mission(
    mission_id: str,
    client: AgentCoreClient = Depends(get_agent_core_client),
) -> Any:
    """Fetch mission status and full state from Agent Core."""
    try:
        return await client.get_mission(mission_id)
    except AgentCoreError as exc:
        raise _map_agent_core_error(exc) from exc


@app.post("/api/v1/missions/{mission_id}/approve")
async def approve_mission(
    mission_id: str,
    client: AgentCoreClient = Depends(get_agent_core_client),
) -> Any:
    """Approve the pending mission; Agent Core resumes the same thread."""
    try:
        return await client.approve_mission(mission_id)
    except AgentCoreError as exc:
        raise _map_agent_core_error(exc) from exc


@app.post("/api/v1/missions/{mission_id}/reject")
async def reject_mission(
    mission_id: str,
    client: AgentCoreClient = Depends(get_agent_core_client),
) -> Any:
    """Reject the pending mission; Agent Core resumes with rejection."""
    try:
        return await client.reject_mission(mission_id)
    except AgentCoreError as exc:
        raise _map_agent_core_error(exc) from exc


def _map_agent_core_error(exc: AgentCoreError) -> HTTPException:
    message = str(exc)
    if "404" in message:
        return HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=message,
        )
    return HTTPException(
        status_code=status.HTTP_502_BAD_GATEWAY,
        detail=message,
    )


@app.exception_handler(AgentCoreError)
async def agent_core_error_handler(
    _request: Any,
    exc: AgentCoreError,
) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_502_BAD_GATEWAY,
        content={"error": str(exc)},
    )
