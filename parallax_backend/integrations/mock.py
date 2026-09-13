from datetime import UTC, datetime
from typing import Any

from parallax_backend.integrations.contracts import (
    AdapterError,
    AdapterHealth,
    ApprovedWriteContext,
    ExternalRecord,
    IntegrationCapability,
    require_approval,
)
from parallax_backend.models import IntegrationProvider


def _fail_if_configured(provider: IntegrationProvider) -> None:
    # Imported lazily to avoid a settings/import cycle in adapter module initialization.
    from parallax_backend.config import settings

    if settings.demo_failure_provider == provider.value:
        raise AdapterError(provider, "Injected local demo failure", retryable=False)


CAPABILITIES: dict[IntegrationProvider, list[IntegrationCapability]] = {
    IntegrationProvider.GITHUB: [
        IntegrationCapability(
            operation="repository.get", access="read", description="Repository metadata"
        ),
        IntegrationCapability(
            operation="pull_request.get", access="read", description="Pull request context"
        ),
        IntegrationCapability(
            operation="pull_request.list", access="read", description="Repository pull requests"
        ),
        IntegrationCapability(
            operation="contents.get", access="read", description="Repository file content"
        ),
    ],
    IntegrationProvider.JIRA: [
        IntegrationCapability(operation="issue.get", access="read", description="Issue metadata"),
        IntegrationCapability(
            operation="issue.search", access="read", description="JQL issue search"
        ),
        IntegrationCapability(
            operation="issue.create", access="write", description="Approved issue creation"
        ),
        IntegrationCapability(
            operation="issue.update", access="write", description="Approved issue update"
        ),
    ],
    IntegrationProvider.NOTION: [
        IntegrationCapability(operation="page.get", access="read", description="Page metadata"),
        IntegrationCapability(operation="page.search", access="read", description="Page search"),
        IntegrationCapability(
            operation="page.append", access="write", description="Approved documentation update"
        ),
    ],
    IntegrationProvider.SLACK: [
        IntegrationCapability(
            operation="channel.history", access="read", description="Channel context"
        ),
        IntegrationCapability(
            operation="message.post", access="write", description="Approved notification"
        ),
        IntegrationCapability(
            operation="message.update", access="write", description="Approved notification update"
        ),
    ],
}


class MockAdapter:
    """Deterministic local adapter. It never makes a network request."""

    def __init__(self, provider: IntegrationProvider):
        self.provider = provider
        self.capabilities = CAPABILITIES[provider]

    async def health(self) -> AdapterHealth:
        _fail_if_configured(self.provider)
        return AdapterHealth(
            provider=self.provider,
            connected=True,
            detail="Connected in deterministic mock mode",
            checked_at=datetime.now(UTC),
        )

    async def close(self) -> None:
        return None


class MockGitHubAdapter(MockAdapter):
    def __init__(self) -> None:
        super().__init__(IntegrationProvider.GITHUB)

    async def get_repository(self, full_name: str) -> ExternalRecord:
        return ExternalRecord(
            provider=self.provider,
            external_id="mock-repository",
            url=f"https://github.com/{full_name}",
            title=full_name,
            data={"full_name": full_name, "default_branch": "main", "mock": True},
        )

    async def get_pull_request(self, full_name: str, number: int) -> ExternalRecord:
        return ExternalRecord(
            provider=self.provider,
            external_id=f"mock-pr-{number}",
            url=f"https://github.com/{full_name}/pull/{number}",
            title=f"Mock PR #{number}",
            data={"number": number, "state": "open", "changed_files": 3, "mock": True},
        )

    async def list_pull_requests(self, full_name: str, state: str = "open") -> list[dict[str, Any]]:
        return [{"id": "mock-pr-1", "number": 1, "title": "Mock PR #1", "state": state}]

    async def get_contents(
        self, full_name: str, path: str, ref: str | None = None
    ) -> dict[str, Any]:
        return {"name": path, "path": path, "ref": ref or "main", "content": "", "mock": True}


class MockJiraAdapter(MockAdapter):
    def __init__(self) -> None:
        super().__init__(IntegrationProvider.JIRA)

    async def get_issue(self, key: str) -> ExternalRecord:
        return ExternalRecord(
            provider=self.provider,
            external_id=key,
            title=f"Mock issue {key}",
            data={"key": key, "status": "In Progress", "mock": True},
        )

    async def search_issues(self, jql: str, max_results: int = 50) -> list[dict[str, Any]]:
        return [{"key": "MOCK-1", "summary": "Mock issue", "jql": jql}][:max_results]

    async def create_issue(
        self, fields: dict[str, Any], approval: ApprovedWriteContext | None
    ) -> ExternalRecord:
        require_approval(approval)
        _fail_if_configured(self.provider)
        return ExternalRecord(
            provider=self.provider,
            external_id="MOCK-1",
            title=str(fields.get("summary", "Mock issue")),
            data={"key": "MOCK-1", "fields": fields, "mock": True},
        )

    async def update_issue(
        self, key: str, fields: dict[str, Any], approval: ApprovedWriteContext | None
    ) -> ExternalRecord:
        require_approval(approval)
        _fail_if_configured(self.provider)
        return ExternalRecord(
            provider=self.provider,
            external_id=key,
            title=str(fields.get("summary", f"Mock issue {key}")),
            data={"key": key, "fields": fields, "mock": True},
        )


class MockNotionAdapter(MockAdapter):
    def __init__(self) -> None:
        super().__init__(IntegrationProvider.NOTION)

    async def get_page(self, page_id: str) -> ExternalRecord:
        return ExternalRecord(
            provider=self.provider,
            external_id=page_id,
            title="Mock Notion page",
            data={"id": page_id, "mock": True},
        )

    async def search_pages(self, query: str) -> list[dict[str, Any]]:
        return [{"id": "mock-page", "title": query or "Mock Notion page", "mock": True}]

    async def append_blocks(
        self,
        page_id: str,
        children: list[dict[str, Any]],
        approval: ApprovedWriteContext | None,
    ) -> ExternalRecord:
        require_approval(approval)
        _fail_if_configured(self.provider)
        return ExternalRecord(
            provider=self.provider,
            external_id=page_id,
            title="Mock Notion page",
            data={"children": children, "mock": True},
        )


class MockSlackAdapter(MockAdapter):
    def __init__(self) -> None:
        super().__init__(IntegrationProvider.SLACK)

    async def channel_history(self, channel: str, max_results: int = 50) -> list[dict[str, Any]]:
        return [{"ts": "1.0", "channel": channel, "text": "Mock message", "mock": True}][
            :max_results
        ]

    async def post_message(
        self, channel: str, text: str, approval: ApprovedWriteContext | None
    ) -> ExternalRecord:
        require_approval(approval)
        _fail_if_configured(self.provider)
        return ExternalRecord(
            provider=self.provider,
            external_id="1.0",
            title="Mock Slack notification",
            data={"channel": channel, "text": text, "mock": True},
        )

    async def update_message(
        self,
        channel: str,
        timestamp: str,
        text: str,
        approval: ApprovedWriteContext | None,
    ) -> ExternalRecord:
        require_approval(approval)
        _fail_if_configured(self.provider)
        return ExternalRecord(
            provider=self.provider,
            external_id=timestamp,
            title="Mock Slack notification",
            data={"channel": channel, "text": text, "mock": True},
        )
