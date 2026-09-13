import hashlib
import json
from dataclasses import dataclass, field
from typing import Any

from app.config import Settings, settings
from app.integrations.contracts import AdapterError
from app.integrations.registry import (
    build_github_adapter,
    build_jira_adapter,
    build_notion_adapter,
)
from app.models import IntegrationProvider, Mission


@dataclass(frozen=True)
class CollectedEvidence:
    key: str
    provider: IntegrationProvider
    external_id: str
    title: str
    excerpt: str
    url: str | None = None
    data: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class CollectedContext:
    summary: str
    content: dict[str, Any]
    content_hash: str
    evidence: list[CollectedEvidence]


def _compact(value: Any, limit: int = 500) -> str:
    return json.dumps(value, sort_keys=True, default=str)[:limit]


async def collect_context(mission: Mission, config: Settings = settings) -> CollectedContext:
    evidence: list[CollectedEvidence] = []
    errors: dict[str, str] = {}
    github = build_github_adapter(config)
    jira = build_jira_adapter(config)
    notion = build_notion_adapter(config)
    try:
        repository = config.github_default_repo or "parallax/demo"
        try:
            pulls = await github.list_pull_requests(repository)
            for index, pull in enumerate(pulls[:20], start=1):
                number = pull.get("number", index)
                evidence.append(
                    CollectedEvidence(
                        key=f"github:pull_request:{number}",
                        provider=IntegrationProvider.GITHUB,
                        external_id=str(pull.get("id", number)),
                        title=str(pull.get("title", f"Pull request #{number}")),
                        excerpt=_compact(pull),
                        url=pull.get("html_url"),
                        data=pull,
                    )
                )
        except AdapterError as exc:
            errors["github"] = str(exc)

        jira_project = config.jira_default_project or mission.project_name.upper().replace(" ", "-")
        try:
            issues = await jira.search_issues(f'project = "{jira_project}" ORDER BY updated DESC')
            for index, issue in enumerate(issues[:20], start=1):
                key = str(issue.get("key", f"ISSUE-{index}"))
                fields = issue.get("fields", {})
                evidence.append(
                    CollectedEvidence(
                        key=f"jira:issue:{key}",
                        provider=IntegrationProvider.JIRA,
                        external_id=key,
                        title=str(fields.get("summary") or issue.get("summary") or key),
                        excerpt=_compact(issue),
                        data=issue,
                    )
                )
        except AdapterError as exc:
            errors["jira"] = str(exc)

        try:
            pages = await notion.search_pages(mission.project_name)
            for index, page in enumerate(pages[:20], start=1):
                page_id = str(page.get("id", f"page-{index}"))
                evidence.append(
                    CollectedEvidence(
                        key=f"notion:page:{page_id}",
                        provider=IntegrationProvider.NOTION,
                        external_id=page_id,
                        title=str(page.get("title") or "Notion page"),
                        excerpt=_compact(page),
                        url=page.get("url"),
                        data=page,
                    )
                )
        except AdapterError as exc:
            errors["notion"] = str(exc)
    finally:
        await github.close()
        await jira.close()
        await notion.close()

    if not evidence:
        evidence.append(
            CollectedEvidence(
                key="notion:page:mission-input",
                provider=IntegrationProvider.NOTION,
                external_id="mission-input",
                title="Manual mission input",
                excerpt=mission.prompt[:500],
                data={"project": mission.project_name, "source": "manual", "fallback": True},
            )
        )
    content = {
        "mission": {"prompt": mission.prompt, "project": mission.project_name},
        "sources": {
            provider.value: sum(item.provider == provider for item in evidence)
            for provider in (
                IntegrationProvider.GITHUB,
                IntegrationProvider.JIRA,
                IntegrationProvider.NOTION,
            )
        },
        "source_errors": errors,
    }
    serialized = json.dumps(
        {"content": content, "evidence": [item.__dict__ for item in evidence]},
        sort_keys=True,
        default=str,
    )
    return CollectedContext(
        summary=(
            f"Collected {len(evidence)} evidence item(s) for {mission.project_name} "
            "from GitHub, Jira, and Notion."
        ),
        content=content,
        content_hash=hashlib.sha256(serialized.encode()).hexdigest(),
        evidence=evidence,
    )
