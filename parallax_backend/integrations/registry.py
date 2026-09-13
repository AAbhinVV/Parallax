from collections.abc import Callable
from typing import Protocol

from parallax_backend.config import Settings, settings
from parallax_backend.integrations.contracts import AdapterHealth, IntegrationCapability
from parallax_backend.integrations.github import GitHubAdapter
from parallax_backend.integrations.jira import JiraAdapter
from parallax_backend.integrations.mock import (
    MockAdapter,
    MockGitHubAdapter,
    MockJiraAdapter,
    MockNotionAdapter,
    MockSlackAdapter,
)
from parallax_backend.integrations.notion import NotionAdapter
from parallax_backend.integrations.slack import SlackAdapter
from parallax_backend.models import IntegrationProvider


class HealthAdapter(Protocol):
    provider: IntegrationProvider
    capabilities: list[IntegrationCapability]

    async def health(self) -> AdapterHealth: ...

    async def close(self) -> None: ...


def build_adapter(provider: IntegrationProvider, config: Settings = settings) -> HealthAdapter:
    if config.integration_mode == "mock":
        mock_adapters: dict[IntegrationProvider, Callable[[], MockAdapter]] = {
            IntegrationProvider.GITHUB: MockGitHubAdapter,
            IntegrationProvider.JIRA: MockJiraAdapter,
            IntegrationProvider.NOTION: MockNotionAdapter,
            IntegrationProvider.SLACK: MockSlackAdapter,
        }
        return mock_adapters[provider]()
    timeout = config.integration_timeout_seconds
    if provider == IntegrationProvider.GITHUB:
        return GitHubAdapter(config.github_token.get_secret_value(), timeout)
    if provider == IntegrationProvider.JIRA:
        return JiraAdapter(
            config.jira_base_url,
            config.jira_email,
            config.jira_api_token.get_secret_value(),
            timeout,
        )
    if provider == IntegrationProvider.NOTION:
        return NotionAdapter(config.notion_token.get_secret_value(), timeout)
    return SlackAdapter(config.slack_bot_token.get_secret_value(), timeout)


def build_github_adapter(config: Settings = settings) -> GitHubAdapter | MockGitHubAdapter:
    if config.integration_mode == "mock":
        return MockGitHubAdapter()
    return GitHubAdapter(config.github_token.get_secret_value(), config.integration_timeout_seconds)


def build_jira_adapter(config: Settings = settings) -> JiraAdapter | MockJiraAdapter:
    if config.integration_mode == "mock":
        return MockJiraAdapter()
    return JiraAdapter(
        config.jira_base_url,
        config.jira_email,
        config.jira_api_token.get_secret_value(),
        config.integration_timeout_seconds,
    )


def build_notion_adapter(config: Settings = settings) -> NotionAdapter | MockNotionAdapter:
    if config.integration_mode == "mock":
        return MockNotionAdapter()
    return NotionAdapter(config.notion_token.get_secret_value(), config.integration_timeout_seconds)


def build_slack_adapter(config: Settings = settings) -> SlackAdapter | MockSlackAdapter:
    if config.integration_mode == "mock":
        return MockSlackAdapter()
    return SlackAdapter(
        config.slack_bot_token.get_secret_value(), config.integration_timeout_seconds
    )
