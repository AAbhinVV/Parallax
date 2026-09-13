# Parallax Backend Structure

```text
Parallax/
├── app/
│   ├── main.py                 # FastAPI application and middleware
│   ├── config.py               # Validated environment configuration
│   ├── database.py             # Async PostgreSQL sessions
│   ├── models.py               # Workspace-scoped SQLAlchemy models
│   ├── schemas.py              # API request and response contracts
│   ├── security.py             # Argon2, JWT, and refresh-token primitives
│   ├── dependencies.py         # Authentication/workspace/role guards
│   ├── queue.py                # Redis connection
│   ├── worker.py               # Separate ARQ worker process
│   ├── metrics.py              # Prometheus instruments
│   ├── integrations/
│   │   ├── contracts.py        # Typed records, health, capabilities, approval proof
│   │   ├── http.py             # Error-normalizing HTTPX transport
│   │   ├── github.py           # GitHub read/context adapter
│   │   ├── jira.py             # Jira read and approval-gated writes
│   │   ├── notion.py           # Notion read and approval-gated writes
│   │   ├── slack.py            # Slack read and approval-gated notifications
│   │   ├── mock.py             # Network-free deterministic equivalents
│   │   └── registry.py         # Real/mock adapter selection
│   └── routers/
│       ├── health.py           # Liveness and dependency readiness
│       ├── auth.py             # Local authentication and token rotation
│       ├── workspaces.py       # Workspace context and membership roles
│       ├── missions.py         # Manual mission commands and reads
│       ├── dashboard.py        # Workspace dashboard projections
│       └── integrations.py     # Four-integration connection status
│   └── services/
│       └── missions.py         # State transitions, DTOs, and audit activity
├── migrations/                 # Alembic PostgreSQL migrations
├── infra/prometheus/           # Local metrics collection
├── docs/
│   ├── API.md                  # Frontend-facing API guide
│   ├── ALIGNMENT.md            # Drive audit and team boundaries
│   └── openapi.json            # Generated API contract
├── scripts/export_openapi.py
├── tests/
├── Dockerfile
└── docker-compose.yml
```

Future business modules are added under `app/modules/`: missions, integrations, context packs, proposals, policy, approvals, execution, verification, audit, and dashboard.

The API handles short request/response work. The worker handles context collection, agent-service calls, retries, external execution, and verification. PostgreSQL is the system of record; Redis is only for jobs, locks, rate limits, and temporary state.

## Identity boundary

Access tokens contain user, workspace, and refresh-session IDs. Every protected request verifies the active user, workspace membership, workspace scope, and non-revoked server-side session. Refresh tokens are random opaque values; only SHA-256 hashes are stored. Passwords are hashed with Argon2id.

Workspace-owned models carry `workspace_id`. Query services must derive this value from the verified request identity rather than accept it as an authorization decision from request bodies.

## Mission processing boundary

```text
Frontend/PM -> FastAPI -> PostgreSQL transaction (mission + outbox + audit)
                              |
                              v
                       outbox dispatcher -> Redis/ARQ -> mission worker
                                                              |
                                                              v
                                                    planning (Phase 3 boundary)
```

PostgreSQL is authoritative. Creating a mission atomically writes the mission, initial transition, activity/audit records, and an outbox job. A periodic worker dispatcher transfers committed outbox jobs to ARQ with a stable job ID. The mission worker then performs a guarded `queued -> planning` transition. This avoids losing work between a database commit and Redis enqueue.

Phase 3 does not collect external context, invoke the Agent service, or mutate integrations. Those boundaries are implemented in Phases 4–7.

## Integration boundary

`INTEGRATION_MODE=mock` is the local default. Mock adapters implement the same typed methods as real adapters and still require approval proof for writes. `INTEGRATION_MODE=real` selects HTTPX clients using environment credentials; secrets are represented as `SecretStr`, never returned by APIs, and never stored in integration configuration JSON.

The adapters currently provide:

- GitHub: repository, pull request, pull request list, and repository-content reads.
- Jira: issue reads/search plus approval-gated create/update.
- Notion: page reads/search plus approval-gated block append.
- Slack: channel history plus approval-gated post/update.

The connection-check API is the only Phase 4 adapter mutation exposed publicly. Business writes remain internal and unreachable until a future execution service loads and validates a persisted approval. Vendor errors are converted to safe `AdapterError` values with retryability metadata; retries and read-after-write verification belong to Phase 7.

## Context and Agent boundary

The Phase 5 worker reads GitHub, Jira, and Notion through the adapter registry and converts every useful source into an evidence item with a stable citation key. PostgreSQL stores the versioned Context Pack, its SHA-256 content hash, source errors, and the exact typed Agent request/response.

```text
mission
  → adapter reads
  → Context Pack + evidence
  → typed read-only Agent request
  → schema, citation, and operation validation
  → persisted assessment and typed proposals
  → context_collected (Phase 5 boundary)
```

The Agent service receives no connector credentials and cannot call integration writes. Responses must cite known evidence keys. GitHub writes and unknown action types are rejected. With fallback enabled, invalid or unavailable Agent output is replaced by a conservative deterministic assessment. Proposals remain inert records until Phase 6 policy and approval.

## Policy, approval, execution, and verification

Phase 6 copies validated Agent proposals into versioned approval bundles. Deterministic policy evaluates operation allowlists, citations, confidence, and provider-specific payload requirements. Edits create a new bundle and rerun policy; approval, rejection, and cancellation are terminal decisions for that version.

Phase 7 turns approval into a transactional outbox job. A Redis compare-and-delete lock prevents concurrent mission execution, while PostgreSQL unique action/idempotency constraints provide durable replay protection. Each action records attempts and a safe error. Successful vendor responses are read back through the adapter before a verification record is written.

```text
context_collected → waiting_for_approval
  → rejected | cancelled
  → running → completed | partially_complete | failed
                  └── retry failed actions only ──┘
```

Verified actions are never repeated during recovery. Partial failure preserves successes and exposes action-level status to frontend and testing teams.

## Analytics and demo-reliability boundary

Phase 8 builds read-only, workspace-scoped projections from PostgreSQL rather than introducing a
second analytics database. Mission timeline and audit endpoints expose durable source records; SLA
and overview endpoints calculate presentation-ready aggregates. Integration health uses the last
persisted check and always returns GitHub, Jira, Notion, and Slack.

Prometheus scrapes API request count, duration, failure, readiness, and build metadata locally.
`X-Trace-ID` equals the request correlation UUID, which is also stored with audit events and emitted
in structured logs. This provides traceable local execution without external telemetry hosting.

Demo reliability tools are deliberately local and explicit: reset deletes only the configured
workspace slug and requires `--confirm`; backup delegates to `pg_dump`; mock failure injection is
off by default and can target Jira, Notion, or Slack without making vendor calls.
