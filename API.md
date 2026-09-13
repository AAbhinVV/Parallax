# Parallax API Contract

FastAPI is the source of truth for the API contract.

## Documentation

| Resource | Local URL | Use |
|---|---|---|
| Swagger UI | `http://localhost:8000/docs` | Interactive reference for frontend and QA |
| ReDoc | `http://localhost:8000/redoc` | Readable API reference |
| OpenAPI JSON | `http://localhost:8000/openapi.json` | Generated client and contract tests |
| Prometheus metrics | `http://localhost:8000/metrics` | Monitoring |

Run `python scripts/export_openapi.py` after changing a route. Commit the resulting `docs/openapi.json`.

## Implemented in Phase 1

### `GET /health`

Process liveness. It does not check dependencies.

```json
{
  "status": "ok",
  "service": "parallax-api",
  "uptime_seconds": 42.5
}
```

### `GET /api/health`

Compatibility path for the Drive MVP. It returns the same response as `GET /health`.

### `GET /ready`

Checks PostgreSQL, Redis, and the worker heartbeat. Returns `200` when all are up and `503` otherwise.

```json
{
  "status": "ready",
  "dependencies": {
    "postgres": "up",
    "redis": "up",
    "worker": "up"
  }
}
```

## Implemented in Phase 3

These paths match `parallax-mvp/frontend/src/api.js` from the shared Drive:

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/api/dashboard/stats` | Dashboard counts and project health |
| `GET` | `/api/dashboard/activity` | Recent verified/audited activity |
| `GET` | `/api/dashboard/projects` | Projects available to the mission form |
| `GET` | `/api/integrations` | GitHub, Jira, Notion, and Slack status |
| `GET` | `/api/missions` | Recent missions |
| `POST` | `/api/missions` | Submit a manual PM/agent-user mission |
| `GET` | `/api/missions/{mission_id}` | Poll mission timeline and result |
| `POST` | `/api/missions/{mission_id}/cancel` | Cancel a non-terminal mission |

The frontend should generate types from `docs/openapi.json`; it must not maintain a second handwritten response schema.

### Required frontend response fields

```text
MissionCreate
  prompt: string
  project: string = "General"

MissionRead
  id: UUID string (treat as an opaque identifier)
  prompt: string
  project: string
  status: queued | planning | context_collected | waiting_for_approval | running |
          completed | blocked | rejected | cancelled | partially_complete | failed
  progress_current: integer
  progress_total: integer
  result_summary: string | null
  steps: MissionStep[]
  created_at: ISO-8601 datetime
  updated_at: ISO-8601 datetime

IntegrationStatus
  name: GitHub | Jira | Notion | Slack
  connected: boolean
  detail: string

DashboardStats
  active_tasks: integer
  completed_this_week: integer
  blocked: integer
  awaiting_approval: integer
  project_health_pct: integer
```

The Drive frontend currently styles `queued`, `running`, `completed`, `blocked`, and `failed`. The frontend team must add styles for approval, rejection, cancellation, and partial completion before those states are enabled.

All Phase 3 routes require an access token. Mission creation and cancellation require the `owner`, `admin`, or `manager` role. Read routes are available to every workspace member. Every query is scoped to the workspace in the access token.

### `POST /api/missions`

Returns `202 Accepted` after the mission and durable job intent are committed together. The API does not call the Agent service inline. `Idempotency-Key` is optional for current frontend compatibility and strongly recommended. Reusing a key with the same body returns the existing mission; reusing it with another body returns `409`.

```http
POST /api/missions
Authorization: Bearer <access-token>
Idempotency-Key: <unique-client-generated-value>
Content-Type: application/json

{"prompt":"Prepare a release-readiness plan","project":"General"}
```

The worker moves a queued mission to `planning` and records the first timeline step. Phase 3 intentionally stops there: context collection and the Agent service gateway belong to Phase 5.

### Mission reads and cancellation

- `GET /api/missions?limit=20&offset=0` returns newest missions first. `limit` is 1–100.
- `GET /api/missions/{mission_id}` returns one mission and its ordered steps. A mission outside the caller's workspace is returned as `404`.
- `POST /api/missions/{mission_id}/cancel` returns the cancelled mission. Cancelling a terminal mission returns `409`.

### Dashboard and integration reads

- `GET /api/dashboard/stats` returns workspace-scoped mission counts and average project health.
- `GET /api/dashboard/activity?limit=10&offset=0` returns newest audit-backed activity first.
- `GET /api/dashboard/projects` returns valid project choices for mission creation.
- `GET /api/integrations` always reports exactly GitHub, Jira, Notion, and Slack for the workspace.

Common errors use `{"detail":"..."}` with `401`, `403`, `404`, `409`, or `422`. Responses include `X-Correlation-ID`; a valid UUID supplied in the request header is preserved.

## Implemented in Phase 4

### `GET /api/integrations/{provider}/capabilities`

Returns the typed operations available for `github`, `jira`, `notion`, or `slack`, their read/write classification, and whether the backend is in `mock` or `real` integration mode. All workspace roles may read capabilities.

### `POST /api/integrations/{provider}/check`

Checks one connection and persists its workspace-scoped status, check time, mode, and safe status message. Requires `owner`, `admin`, or `manager`. The result is recorded in the audit log.

```json
{
  "name": "GitHub",
  "connected": true,
  "detail": "Connected in deterministic mock mode"
}
```

In `mock` mode no third-party network request is made. In `real` mode missing credentials produce `connected: false`; normalized vendor/network failures return `502` without exposing tokens or vendor response bodies.

Phase 4 does not publish integration data or mutation endpoints. GitHub/Jira/Notion reads are invoked internally by the Phase 5 context worker. Jira, Notion, and Slack write methods require a typed, previously validated approval context and will be wired to persisted approvals only in Phases 6–7.

## Implemented in Phase 5

### `GET /api/missions/{mission_id}/context-pack`

Returns the latest workspace-scoped Context Pack, its SHA-256 content hash, source counts/errors, and ordered evidence. Evidence keys such as `github:pull_request:1` are stable citation identifiers. A missing or cross-workspace Context Pack returns `404`.

### `GET /api/missions/{mission_id}/assessment`

Returns the validated Agent result: context summary, risk and factors, review effort, ranked reviewer candidates, confidence, explanation, citations, typed proposals, and whether the result came from `service` or `fallback` mode. A missing or cross-workspace assessment returns `404`.

Mission processing now follows:

```text
queued → planning → context_collected
```

At `context_collected`, three timeline steps are complete and the Context Pack plus assessment are available. The mission intentionally remains there until Phase 6 evaluates policy and creates an approval bundle.

The Agent request is read-only and contains no integration credentials. The backend rejects unknown citations, malformed response fields, duplicate top-level citations, unsupported operations, and every GitHub write proposal. If configured, an invalid or unavailable Agent service produces a conservative deterministic fallback rather than fabricated completion.

## Implemented in Phase 6

- `POST /api/missions/{mission_id}/approval` creates or returns the latest policy-checked approval bundle.
- `GET /api/approvals/{approval_id}` returns its version, policy result, typed actions, and decision.
- `POST /api/approvals/{approval_id}/approve` approves the exact stored version and queues execution.
- `POST /api/approvals/{approval_id}/edit` creates a new version and reruns all policy checks.
- `POST /api/approvals/{approval_id}/reject` rejects all proposed actions.
- `POST /api/approvals/{approval_id}/cancel` cancels the approval and mission.

Approval mutations require `owner`, `admin`, or `manager`. Decisions are one-time: repeating or changing a terminal decision returns `409`. Edits never mutate the original bundle. Policy rejects unknown citations, unsupported operations, GitHub writes, low-confidence assessments, and provider payloads missing required fields. Every integration write requires explicit approval.

## Implemented in Phase 7

- `GET /api/missions/{mission_id}/executions` returns action attempts, safe errors, external IDs, results, and verification evidence.
- `POST /api/missions/{mission_id}/retry` requeues only failed actions for a `failed`, `blocked`, or `partially_complete` mission.

Approval and its execution outbox intent commit atomically. The worker uses a Redis ownership lock plus a unique action idempotency key, skips already verified actions, limits retries, and reads Jira, Notion, or Slack back before marking success. Outcomes are `completed`, `partially_complete`, or `failed`; an API success without read-after-write evidence is never treated as verified.

## Implemented in Phase 8

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/api/missions/{mission_id}/timeline` | Ordered, durable mission transitions |
| `GET` | `/api/missions/{mission_id}/sla` | Mission age, target, remaining time, and breach state |
| `GET` | `/api/audit-events` | Paginated workspace audit feed; filter by mission or event type |
| `GET` | `/api/analytics/overview` | Mission completion and execution-verification aggregates |
| `GET` | `/api/integrations/health` | Stored health status for GitHub, Jira, Notion, and Slack |

All Phase 8 endpoints require authentication and are scoped to the workspace in the access token.
Cross-workspace mission timeline/SLA reads return `404`. Audit pagination supports `limit` (1–200)
and `offset`; analytics returns all mission statuses and all four providers, including zero counts, so
frontend charts do not need to invent missing categories.

Every API response includes `X-Correlation-ID` and `X-Trace-ID`. They contain the same UUID in this
local architecture, letting frontend, QA, API logs, audit records, and worker records refer to one
operation without requiring a cloud tracing service.

## Implemented in Phase 2

Protected routes use:

```http
Authorization: Bearer <access-token>
X-Workspace-ID: <workspace-uuid>
```

`X-Workspace-ID` is optional because the access token is already workspace-scoped. If supplied, it must match the token. To change workspaces, log in with the desired `workspace_id` and receive a newly scoped token.

### `POST /api/auth/register`

Creates a user, workspace, owner membership, and token session atomically. Returns `201`. Duplicate email or workspace slug returns `409`.

```json
{
  "email": "owner@example.com",
  "password": "a-password-with-12-or-more-characters",
  "display_name": "Example Owner",
  "workspace_name": "Example Engineering",
  "workspace_slug": "example-engineering"
}
```

### `POST /api/auth/login`

Authenticates a local user. `workspace_id` is optional; when omitted, the oldest membership is selected. Returns an access token and opaque refresh token.

### `POST /api/auth/refresh`

Rotates the supplied refresh token. The old refresh session and its access token become invalid immediately.

### `POST /api/auth/logout`

Revokes the refresh session. Returns `204` with no response body.

### `GET /api/auth/me`

Returns the current user, active workspace, role, and available workspaces. Password and token hashes are never returned.

### `GET /api/workspaces/current`

Returns the workspace and role derived from the access token.

### `GET /api/workspaces/current/members`

Lists members of the token-scoped workspace. Requires authentication.

### `PATCH /api/workspaces/current/members/{user_id}`

Changes a member role. Requires owner or admin. Only owners may manage the owner role, and a workspace must retain at least one owner.

Available roles are `owner`, `admin`, `manager`, `reviewer`, and `viewer`.

## Endpoint documentation rule

Every endpoint must declare a tag, summary, request model, response model, error responses, and stable status codes. Mutation endpoints must also document idempotency and approval behavior.
