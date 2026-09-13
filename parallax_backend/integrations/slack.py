from datetime import UTC, datetime
from typing import Any

import httpx

from parallax_backend.integrations.contracts import (
    AdapterError,
    AdapterHealth,
    ApprovedWriteContext,
    ExternalRecord,
    IntegrationCapability,
    require_approval,
)
from parallax_backend.integrations.http import VendorHttpClient
from parallax_backend.models import IntegrationProvider


class SlackAdapter:
    provider = IntegrationProvider.SLACK
    capabilities = [
        IntegrationCapability(
            operation="channel.history", access="read", description="Read channel context"
        ),
        IntegrationCapability(
            operation="message.post", access="write", description="Post an approved notification"
        ),
        IntegrationCapability(
            operation="message.update",
            access="write",
            description="Update an approved notification",
        ),
    ]

    def __init__(
        self, token: str, timeout: float, transport: httpx.AsyncBaseTransport | None = None
    ):
        self.configured = bool(token)
        self.http = VendorHttpClient(
            self.provider,
            "https://slack.com/api",
            {"Authorization": f"Bearer {token}", "Content-Type": "application/json; charset=utf-8"},
            timeout,
            transport,
        )

    async def _call(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        data: dict[str, Any] = await self.http.request(method, path, **kwargs)
        if not data.get("ok", False):
            raise AdapterError(
                self.provider, f"Slack API error: {data.get('error', 'unknown_error')}"
            )
        return data

    async def health(self) -> AdapterHealth:
        if not self.configured:
            return AdapterHealth(
                provider=self.provider,
                connected=False,
                detail="Missing SLACK_BOT_TOKEN",
                checked_at=datetime.now(UTC),
            )
        data = await self._call("POST", "/auth.test")
        return AdapterHealth(
            provider=self.provider,
            connected=True,
            detail=f"Connected as {data.get('user', 'Slack bot')}",
            checked_at=datetime.now(UTC),
        )

    async def channel_history(self, channel: str, limit: int = 50) -> list[dict[str, Any]]:
        data = await self._call(
            "GET", "/conversations.history", params={"channel": channel, "limit": limit}
        )
        return list(data.get("messages", []))

    async def post_message(
        self, channel: str, text: str, approval: ApprovedWriteContext | None
    ) -> ExternalRecord:
        require_approval(approval)
        data = await self._call(
            "POST", "/chat.postMessage", json={"channel": channel, "text": text}
        )
        return ExternalRecord(
            provider=self.provider,
            external_id=str(data["ts"]),
            title="Slack notification",
            data=data,
        )

    async def update_message(
        self, channel: str, timestamp: str, text: str, approval: ApprovedWriteContext | None
    ) -> ExternalRecord:
        require_approval(approval)
        data = await self._call(
            "POST", "/chat.update", json={"channel": channel, "ts": timestamp, "text": text}
        )
        return ExternalRecord(
            provider=self.provider,
            external_id=str(data["ts"]),
            title="Slack notification",
            data=data,
        )

    async def close(self) -> None:
        await self.http.close()
