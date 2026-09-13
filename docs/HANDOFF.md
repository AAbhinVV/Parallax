# Backend Handoff

## Current state

- Branch: `feature/backend-development`
- Phase 1: complete and committed as `b5ff4ec`
- Phase 2: complete and committed as `16016b4`
- Phase 3: complete and committed as `e3f8027`
- Phase 4: complete and committed as `1809c98`
- Phase 5: complete and committed as `5030171`
- Phase 6 and 7: complete and committed as `a5f141f`
- Phase 8: complete and verified in the working tree; awaiting commit
- Next milestone: frontend/Agent/deployment-team integration and live-vendor acceptance testing

## Phase 3 implementation

Frontend/API endpoints:

- `POST /api/missions`
- `GET /api/missions`
- `GET /api/missions/{mission_id}`
- `POST /api/missions/{mission_id}/cancel`
- `GET /api/dashboard/stats`
- `GET /api/dashboard/activity`
- `GET /api/dashboard/projects`
- `GET /api/integrations`

Persistence added for missions, ordered steps, state transitions, activity, immutable-style audit events, idempotency records, and transactional outbox jobs. Manual submission commits the initial mission and job intent atomically. The worker dispatches the outbox to ARQ with a stable job ID and advances the mission from `queued` to `planning`.

The mission state machine rejects illegal transitions. Mission reads, dashboard projections, projects, integrations, idempotency keys, and correlation IDs are all workspace-scoped.

## Phase 4 implementation

- Real HTTPX clients for GitHub, Jira, Notion, and Slack
- Deterministic network-free mock implementations with matching contracts
- Typed external records, capabilities, health results, and write-approval context
- Safe vendor/network error normalization
- Environment-only credentials using Pydantic secret types
- Workspace-scoped, role-protected connection checks with audit records
- Capability discovery endpoint for frontend and test teams
- Approval required before any Jira, Notion, or Slack adapter write reaches the network

No public integration business-write endpoint exists yet. Phase 6 must persist approvals, and Phase 7 must load that record before constructing `ApprovedWriteContext` and invoking a write method.

## Phase 5 implementation

- Worker collection from GitHub, Jira, and Notion through Phase 4 contracts
- Versioned Context Packs with SHA-256 hashes and citation-addressable evidence
- Typed, read-only `POST /v1/analyze` Agent-team contract
- Validation for risk, effort, reviewers, confidence, citations, and allowed proposals
- Deterministic conservative fallback for local demos and invalid/unavailable Agent responses
- Persisted Agent runs, request/response records, assessments, source errors, and audit timeline
- Workspace-scoped Context Pack and assessment read APIs

The Agent receives evidence but never connector credentials. Its proposals are stored as untrusted typed data; nothing is executed. The worker finishes at `context_collected`, leaving policy and approval to Phase 6.

## Phase 6 implementation

- Persisted typed action proposals and versioned approval bundles
- Deterministic policy allowlists, evidence validation, confidence threshold, and payload rules
- Approval preparation, read, approve, edit/revalidate, reject, and cancel APIs
- Workspace/role isolation, one-time decisions, state transitions, and audit activity

## Phase 7 implementation

- Approval-to-execution transactional outbox handoff
- ARQ execution worker with Redis ownership lock and PostgreSQL idempotency constraints
- Bounded retry attempts and safe action-level errors
- Jira, Notion, and Slack approved writes; GitHub remains read-only
- Mandatory read-after-write verification records
- Completed, partial, and failed outcomes plus failed-action recovery API
- Replay skips verified actions and preserves prior verification

## Existing Phase 2 foundation

Models:

- users
- workspaces
- workspace memberships
- teams
- projects
- repositories
- integrations
- external identities
- refresh sessions

All identifiers are UUIDs. Every workspace-owned model contains `workspace_id`. Workspace roles are owner, admin, manager, reviewer, and viewer.
Registration and demo seeding create disconnected GitHub, Jira, Notion, and Slack integration records for the workspace.

Authentication endpoints:

- `POST /api/auth/register`
- `POST /api/auth/login`
- `POST /api/auth/refresh`
- `POST /api/auth/logout`
- `GET /api/auth/me`

Workspace endpoints:

- `GET /api/workspaces/current`
- `GET /api/workspaces/current/members`
- `PATCH /api/workspaces/current/members/{user_id}`

## Security decisions

- Argon2id password hashes
- HS256 access JWTs with a 15-minute default lifetime
- Opaque random refresh tokens; only SHA-256 token hashes are stored
- Server-side refresh sessions support rotation, logout, and access-token revocation
- Access tokens are scoped to exactly one workspace and membership is checked on every protected request
- Admins cannot manage the owner role; the last owner cannot be demoted
- Raw credentials, password hashes, and token hashes are not exposed by APIs

## Migration

`20260913_0005_policy_approvals` and `20260913_0006_execution_verification` follow the Phase-5 migration.

## Environment variables

- `JWT_SECRET`
- `JWT_ACCESS_TOKEN_MINUTES`
- `JWT_REFRESH_TOKEN_DAYS`
- `AGENT_MODE` (`fallback` or `service`)
- `AGENT_SERVICE_URL`
- `AGENT_SERVICE_API_KEY`
- `AGENT_TIMEOUT_SECONDS`
- `AGENT_FALLBACK_ENABLED`
- `EXECUTION_MAX_ATTEMPTS`
- `EXECUTION_LOCK_TTL_SECONDS`
- optional `DEMO_OWNER_*` and `DEMO_WORKSPACE_*` variables for local seeding

## Commands

```bash
alembic upgrade head
ruff check .
mypy app scripts/seed_demo.py
pytest
python scripts/export_openapi.py
docker compose up --build -d
```

## Current boundary

- Real vendor writes are not acceptance-tested without user-supplied credentials; deterministic mock execution is the local verification target.
- Real adapters are implemented but live credentials were not supplied, so vendor acceptance tests are not claimed.
- Mock writes are deterministic in memory; Phase 7 owns persisted execution records, idempotency, retries, and verification.
- GitHub remains read-only for the current Phase 4 scope.
- Local registration remains intentionally open for the local MVP.

## Verification result

- Ruff: passed
- strict MyPy: passed for the app and all operational scripts
- Pytest: 30 passed, including analytics, workspace isolation, failure injection, approval decisions, idempotent execution, verification, partial failure, and recovery
- Generated OpenAPI contract: refreshed
- Target PostgreSQL revision: `20260913_0006 (head)`
- Alembic schema drift check: no new upgrade operations
- Docker: API healthy; PostgreSQL and Redis healthy; worker running
- Readiness: `ready`; Prometheus API target: `up`
- Manual Phase 5 smoke: mission reached `context_collected`, 3 evidence items, fallback assessment, 2 typed proposals, and 0 unknown citations
- Worker jobs observed: zero failed and zero retried
# Phase 8 frontend and QA handoff

- Generate frontend types from `docs/openapi.json` after this phase.
- Use `/api/missions/{id}/timeline` for the durable execution timeline.
- Use `/api/missions/{id}/sla` for countdown/breach UI; do not calculate the target in the browser.
- Use `/api/analytics/overview` for charts; every status/provider is returned even at zero.
- Use `/api/audit-events` for a paginated audit screen and `/api/integrations/health` for detailed
  integration state.
- Include `X-Correlation-ID` when reporting a failure; the response `X-Trace-ID` matches it.
- QA can set `DEMO_FAILURE_PROVIDER` only in mock mode to exercise partial/failed recovery.
