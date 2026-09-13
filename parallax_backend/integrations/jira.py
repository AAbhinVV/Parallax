import base64
from datetime import UTC, datetime
from typing import Any

import httpx

from parallax_backend.integrations.contracts import (
    AdapterHealth,
    ApprovedWriteContext,
    ExternalRecord,
    IntegrationCapability,
    require_approval,
)
from parallax_backend.integrations.http import VendorHttpClient
from parallax_backend.models import IntegrationProvider


class JiraAdapter:
    provider = IntegrationProvider.JIRA
    capabilities = [
        IntegrationCapability(operation="issue.get", access="read", description="Issue metadata"),
        IntegrationCapability(
            operation="issue.search", access="read", description="Search issues with JQL"
        ),
        IntegrationCapability(
            operation="issue.create", access="write", description="Create an approved issue"
        ),
        IntegrationCapability(
            operation="issue.update", access="write", description="Update an approved issue"
        ),
    ]

    def __init__(
        self,
        base_url: str,
        email: str,
        token: str,
        timeout: float,
        transport: httpx.AsyncBaseTransport | None = None,
    ):
        self.configured = bool(base_url and email and token)
        auth = base64.b64encode(f"{email}:{token}".encode()).decode()
        self.http = VendorHttpClient(
            self.provider,
            base_url or "https://not-configured.invalid",
            {
                "Accept": "application/json",
                "Content-Type": "application/json",
                "Authorization": f"Basic {auth}",
            },
            timeout,
            transport,
        )

    async def health(self) -> AdapterHealth:
        if not self.configured:
            return AdapterHealth(
                provider=self.provider,
                connected=False,
                detail="Missing Jira URL, email, or API token",
                checked_at=datetime.now(UTC),
            )
        data = await self.http.request("GET", "/rest/api/3/myself")
        return AdapterHealth(
            provider=self.provider,
            connected=True,
            detail=f"Authenticated as {data.get('displayName', 'Jira user')}",
            checked_at=datetime.now(UTC),
        )

    async def get_issue(self, key: str) -> ExternalRecord:
        data: dict[str, Any] = await self.http.request("GET", f"/rest/api/3/issue/{key}")
        fields = data.get("fields", {})
        return ExternalRecord(
            provider=self.provider,
            external_id=str(data.get("key", key)),
            title=str(fields.get("summary", key)),
            data=data,
        )

    async def search_issues(self, jql: str, max_results: int = 50) -> list[dict[str, Any]]:
        data: dict[str, Any] = await self.http.request(
            "POST", "/rest/api/3/search/jql", json={"jql": jql, "maxResults": max_results}
        )
        return list(data.get("issues", []))

    async def create_issue(
        self, fields: dict[str, Any], approval: ApprovedWriteContext | None
    ) -> ExternalRecord:
        require_approval(approval)
        data: dict[str, Any] = await self.http.request(
            "POST", "/rest/api/3/issue", json={"fields": fields}
        )
        return ExternalRecord(
            provider=self.provider,
            external_id=str(data["key"]),
            title=str(fields.get("summary", data["key"])),
            data=data,
        )

    async def update_issue(
        self, key: str, fields: dict[str, Any], approval: ApprovedWriteContext | None
    ) -> ExternalRecord:
        require_approval(approval)
        await self.http.request("PUT", f"/rest/api/3/issue/{key}", json={"fields": fields})
        return await self.get_issue(key)

    async def close(self) -> None:
        await self.http.close()
