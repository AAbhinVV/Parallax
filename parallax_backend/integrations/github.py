from datetime import UTC, datetime
from typing import Any

import httpx

from parallax_backend.integrations.contracts import (
    AdapterHealth,
    ExternalRecord,
    IntegrationCapability,
)
from parallax_backend.integrations.http import VendorHttpClient
from parallax_backend.models import IntegrationProvider


class GitHubAdapter:
    provider = IntegrationProvider.GITHUB
    capabilities = [
        IntegrationCapability(
            operation="repository.get", access="read", description="Repository metadata"
        ),
        IntegrationCapability(
            operation="pull_request.get",
            access="read",
            description="Pull request metadata and diff",
        ),
        IntegrationCapability(
            operation="pull_request.list", access="read", description="Repository pull requests"
        ),
        IntegrationCapability(
            operation="contents.get", access="read", description="CODEOWNERS and repository files"
        ),
    ]

    def __init__(
        self, token: str, timeout: float, transport: httpx.AsyncBaseTransport | None = None
    ):
        self.configured = bool(token)
        self.http = VendorHttpClient(
            self.provider,
            "https://api.github.com",
            {
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {token}",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            timeout,
            transport,
        )

    async def health(self) -> AdapterHealth:
        if not self.configured:
            return AdapterHealth(
                provider=self.provider,
                connected=False,
                detail="Missing GITHUB_TOKEN",
                checked_at=datetime.now(UTC),
            )
        data = await self.http.request("GET", "/user")
        return AdapterHealth(
            provider=self.provider,
            connected=True,
            detail=f"Authenticated as {data.get('login', 'GitHub user')}",
            checked_at=datetime.now(UTC),
        )

    async def get_repository(self, full_name: str) -> ExternalRecord:
        data: dict[str, Any] = await self.http.request("GET", f"/repos/{full_name}")
        return ExternalRecord(
            provider=self.provider,
            external_id=str(data["id"]),
            url=data.get("html_url"),
            title=str(data.get("full_name", full_name)),
            data=data,
        )

    async def get_pull_request(self, full_name: str, number: int) -> ExternalRecord:
        data: dict[str, Any] = await self.http.request("GET", f"/repos/{full_name}/pulls/{number}")
        return ExternalRecord(
            provider=self.provider,
            external_id=str(data["id"]),
            url=data.get("html_url"),
            title=str(data.get("title", f"PR #{number}")),
            data=data,
        )

    async def list_pull_requests(self, full_name: str, state: str = "open") -> list[dict[str, Any]]:
        data: list[dict[str, Any]] = await self.http.request(
            "GET", f"/repos/{full_name}/pulls", params={"state": state}
        )
        return data

    async def get_contents(
        self, full_name: str, path: str, ref: str | None = None
    ) -> dict[str, Any]:
        params = {"ref": ref} if ref else None
        data: dict[str, Any] = await self.http.request(
            "GET", f"/repos/{full_name}/contents/{path.lstrip('/')}", params=params
        )
        return data

    async def close(self) -> None:
        await self.http.close()
