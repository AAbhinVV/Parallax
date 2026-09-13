# Parallax Backend Pipeline

## Scope

- Input is entered manually by a PM or agent user.
- GitHub webhooks are not an input in the current version.
- Integrations are GitHub, Jira, Notion, and Slack.
- Everything runs locally with Docker Compose; no cloud host is required.

## Pipeline

```text
Manual PM / Agent User Mission
        ↓
FastAPI validates and saves the mission in PostgreSQL
        ↓
API places a job in Redis and returns the mission ID immediately
        ↓
Worker reads GitHub, Jira, and Notion through isolated adapters
        ↓
Backend saves evidence and sends typed, read-only context to the Agent service
        ↓
Agent returns analysis, confidence, citations, and proposed actions
        ↓
Backend validates the response and applies deterministic policy
        ↓
Frontend shows the action preview for approve / edit / reject / cancel
        ↓
Worker executes only approved Slack, Jira, Notion, or permitted GitHub actions
        ↓
Worker reads the external systems back to verify the changes
        ↓
Backend records results, errors, retries, evidence, and audit events
        ↓
Frontend polls the mission timeline and final report
```

## Backend stack

| Area | Technology | Why |
|---|---|---|
| Language | Python 3.12 | Matches the Drive backend and agent ecosystem |
| API | FastAPI + Pydantic | Typed validation and automatic OpenAPI docs |
| Database | PostgreSQL | Durable source of truth for missions, approvals, evidence, and audit |
| ORM/migrations | SQLAlchemy 2 + Alembic | Async database access and versioned schema changes |
| Queue/cache | Redis | Jobs, locks, rate limits, and temporary state |
| Worker | ARQ | Lightweight async Python worker for the local MVP |
| Integrations | HTTPX adapters | Narrow, testable clients for GitHub, Jira, Notion, and Slack |
| Logs | Structlog | Searchable JSON logs with correlation and mission IDs |
| Monitoring | Prometheus | Local health and performance visibility |
| API contract | OpenAPI | Shared source of truth for frontend and QA |
| Runtime | Docker Compose | Reproducible local stack without cloud hosting |
| Tests | Pytest + HTTPX | Unit and API testing in Python |

