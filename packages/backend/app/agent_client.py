"""Async client for the Parallax Agent Core HTTP API.

The FastAPI backend is strictly a control-plane layer:
it forwards missions to Agent Core (:4010) and relays
mission state back to callers. All planning, approval,
execution, verification and audit logic lives in Agent Core.
"""

from __future__ import annotations

from typing import Any

import httpx

from .config import AGENT_CORE_TIMEOUT_SECONDS, AGENT_CORE_URL


class AgentCoreError(Exception):
    """Raised when Agent Core returns an unexpected response."""


class AgentCoreClient:
    """Thin async wrapper around the Agent Core HTTP API."""

    def __init__(
        self,
        base_url: str = AGENT_CORE_URL,
        timeout: float = AGENT_CORE_TIMEOUT_SECONDS,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._client = httpx.AsyncClient(
            base_url=base_url,
            timeout=timeout,
            transport=transport,
        )

    async def aclose(self) -> None:
        await self._client.aclose()

    async def create_mission(
        self,
        mission: str,
        mission_id: str | None = None,
    ) -> dict[str, Any]:
        """POST /missions — start a mission and return its initial state."""
        payload: dict[str, Any] = {"mission": mission}
        if mission_id is not None:
            payload["missionId"] = mission_id

        return await self._request("POST", "/missions", json=payload)

    async def get_mission(self, mission_id: str) -> dict[str, Any]:
        """GET /missions/{id} — fetch stored mission status and state."""
        return await self._request("GET", f"/missions/{mission_id}")

    async def approve_mission(
        self,
        mission_id: str,
    ) -> dict[str, Any]:
        """POST /missions/{id}/approve — resume the agent thread."""
        return await self._request(
            "POST",
            f"/missions/{mission_id}/approve",
        )

    async def reject_mission(
        self,
        mission_id: str,
    ) -> dict[str, Any]:
        """POST /missions/{id}/reject — resume with a rejection."""
        return await self._request(
            "POST",
            f"/missions/{mission_id}/reject",
        )

    async def _request(
        self,
        method: str,
        path: str,
        **kwargs: Any,
    ) -> dict[str, Any]:
        try:
            response = await self._client.request(method, path, **kwargs)
        except httpx.HTTPError as exc:
            raise AgentCoreError(
                f"Agent Core is unreachable at {self._client.base_url}: {exc}",
            ) from exc

        try:
            body: dict[str, Any] = response.json()
        except ValueError as exc:
            raise AgentCoreError(
                f"Agent Core returned invalid JSON ({response.status_code}).",
            ) from exc

        if response.status_code >= 400:
            detail = body.get("error", response.text)
            raise AgentCoreError(
                f"Agent Core error ({response.status_code}): {detail}",
            )

        return body
