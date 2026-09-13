from datetime import UTC, datetime
from typing import Any

import httpx

from app.integrations.contracts import (
    AdapterHealth,
    ApprovedWriteContext,
    ExternalRecord,
    IntegrationCapability,
    require_approval,
)
from app.integrations.http import VendorHttpClient
from app.models import IntegrationProvider


class NotionAdapter:
    provider = IntegrationProvider.NOTION
    capabilities = [
        IntegrationCapability(operation="page.get", access="read", description="Page metadata"),
        IntegrationCapability(
            operation="page.search", access="read", description="Search accessible pages"
        ),
        IntegrationCapability(
            operation="page.append", access="write", description="Append approved documentation"
        ),
    ]

    def __init__(
        self, token: str, timeout: float, transport: httpx.AsyncBaseTransport | None = None
    ):
        self.configured = bool(token)
        self.http = VendorHttpClient(
            self.provider,
            "https://api.notion.com",
            {
                "Authorization": f"Bearer {token}",
                "Notion-Version": "2022-06-28",
                "Content-Type": "application/json",
            },
            timeout,
            transport,
        )

    async def health(self) -> AdapterHealth:
        if not self.configured:
            return AdapterHealth(
                provider=self.provider,
                connected=False,
                detail="Missing NOTION_TOKEN",
                checked_at=datetime.now(UTC),
            )
        data = await self.http.request("GET", "/v1/users/me")
        return AdapterHealth(
            provider=self.provider,
            connected=True,
            detail=f"Connected as {data.get('name') or 'Notion integration'}",
            checked_at=datetime.now(UTC),
        )

    async def get_page(self, page_id: str) -> ExternalRecord:
        data: dict[str, Any] = await self.http.request("GET", f"/v1/pages/{page_id}")
        return ExternalRecord(
            provider=self.provider,
            external_id=str(data.get("id", page_id)),
            url=data.get("url"),
            title="Notion page",
            data=data,
        )

    async def search_pages(self, query: str) -> list[dict[str, Any]]:
        data: dict[str, Any] = await self.http.request(
            "POST",
            "/v1/search",
            json={"query": query, "filter": {"property": "object", "value": "page"}},
        )
        return list(data.get("results", []))

    async def append_blocks(
        self, page_id: str, children: list[dict[str, Any]], approval: ApprovedWriteContext | None
    ) -> ExternalRecord:
        require_approval(approval)
        data: dict[str, Any] = await self.http.request(
            "PATCH", f"/v1/blocks/{page_id}/children", json={"children": children}
        )
        return ExternalRecord(
            provider=self.provider, external_id=page_id, title="Notion page update", data=data
        )

    async def close(self) -> None:
        await self.http.close()
