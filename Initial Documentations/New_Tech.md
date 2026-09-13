Recommended architecture:

- **TypeScript**
- Node.js runtime
- NestJS or a modular Fastify-based application
- tRPC for internal typed APIs where useful
- REST/Webhooks for external integrations
- OpenAPI for public/internal boundary documentation

Use a modular monolith for the first production release, with explicit domain modules.

Do not start with dozens of microservices.

---

# 3. Core backend modules

```text
/auth
/tenancy
/users
/teams
/integrations
/events
/github
/slack
/jira
/linear
/notion
/calendar
/pr-intelligence
/context-packs
/risk
/reviewer-routing
/scheduling
/missions
/planner
/policy
/approvals
/execution
/verification
/audit
/analytics
/notifications
```

Each module owns its domain logic and should expose stable internal interfaces.

---

# 4. Data layer

## Primary relational database

**PostgreSQL**

Use for:

- tenants
- users
- teams
- integrations
- repository metadata
- PR metadata
- context packs
- reviewer assignments
- missions
- action proposals
- approvals
- execution records
- audit records
- analytics aggregates

Use row-level security only where it provides real additional defense; application-level tenant scoping must still be enforced.

## Cache / ephemeral state

**Redis**

Use for:

- rate limits
- short-lived locks
- job state
- deduplication windows
- session-adjacent ephemeral data
- frequently requested computed views

Do not use Redis as the system of record.

## Search

Start with PostgreSQL full-text + pgvector if required.

Introduce OpenSearch only when:

- audit/activity search becomes large,
- cross-document search requirements exceed Postgres,
- or operational logs need a dedicated search plane.

## Object storage

S3-compatible object storage for:

- exported reports
- large evidence artifacts
- optional model inputs/outputs
- retained snapshots where policy permits

---

# 5. Eventing and jobs

Recommended first approach:

- Postgres-backed outbox
- Durable job queue
- Redis-based workers or a managed queue
- Webhook ingestion endpoint

Candidate platforms:

- BullMQ
- Trigger.dev
- Temporal for complex durable workflows

## Recommendation

Use **Temporal** when multi-step execution becomes mission-critical.

Why:

Missions may involve:

- pauses for approval
- retries
- external APIs
- timers
- escalations
- human tasks
- long-running execution

Temporal fits this execution model better than a simple request-response job queue.

---

# 6. AI / agent stack

## Model layer

Use a provider abstraction:

```text
ModelGateway
  ├── primary model
  ├── fast/low-cost model
  ├── embeddings model
  └── optional self-hosted model
```

Do not couple product logic directly to one model provider.

## Agent orchestration

Use an explicit state-machine or graph-based orchestration layer.

Good fit:

- LangGraph
- Temporal + application-level reasoning nodes
- custom typed workflow engine

### Recommended

**Temporal for durable execution + LangGraph-style explicit reasoning graphs where agentic branching is required.**

Avoid an opaque "autonomous agent" loop.

---

# 7. LLM task separation

Not every task should call an LLM.

| Task | Preferred mechanism |
|---|---|
| Event deduplication | deterministic |
| PR metadata | API |
| Ticket matching | deterministic + semantic ranking |
| Code ownership | CODEOWNERS/git history |
| Risk signals | rules + model |
| Summary | LLM |
| Reasoning explanation | LLM |
| Reviewer ranking | weighted deterministic model |
| Calendar availability | deterministic |
| Policy check | deterministic |
| Action execution | deterministic API call |
| Verification | deterministic API observation |

This reduces cost, latency, and hallucination risk.

---

# 8. AI-generated PR detection

Do not assume a single classifier.

Use a layered signal:

### Source signals
- bot-authored branch/commit patterns
- known coding-agent identities
- generated commit conventions
- PR metadata patterns
- tool-specific markers

### Behavioral signals
- unusual commit cadence
- branch naming patterns
- author identity relationships
- machine-like PR description patterns

### Optional model signal

A model may estimate probability from metadata and text, but this must remain a confidence signal—not a fact.

Expose:

`AI-generated likelihood: 0–100%`

rather than a binary label when evidence is uncertain.

---

# 9. Integrations

## GitHub

Use GitHub App authentication rather than personal access tokens wherever feasible.

Capabilities:

- PRs
- issues
- repositories
- commits
- reviews
- checks
- comments
- labels
- CODEOWNERS
- webhook events

## Slack

Use Slack app/bot integration for:

- channels
- notifications
- interactive actions
- approval links
- mission updates

## Jira / Linear

Support one first and design the connector interface for both.

Common connector contract:

```ts
interface ProjectManagementConnector {
  searchIssues(query: IssueQuery): Promise<Issue[]>;
  getIssue(id: string): Promise<Issue>;
  createIssue(input: CreateIssueInput): Promise<Issue>;
  updateIssue(id: string, input: UpdateIssueInput): Promise<Issue>;
  addComment(id: string, body: string): Promise<void>;
  linkExternalRecord(id: string, link: ExternalLink): Promise<void>;
}
```

## Notion

Use for project memory and mission reports.

## Google Calendar

Use for:

- availability
- review block proposals
- scheduling
- cancellation/reschedule handling

---

# 10. API architecture

Use versioned REST for integration-facing endpoints.

Example:

```text
POST /api/v1/webhooks/github
POST /api/v1/webhooks/slack

GET  /api/v1/prs
GET  /api/v1/prs/:id
GET  /api/v1/prs/:id/context-pack
GET  /api/v1/prs/:id/review-plan

POST /api/v1/missions
GET  /api/v1/missions/:id
POST /api/v1/missions/:id/approve
POST /api/v1/missions/:id/reject

GET  /api/v1/review-debt
GET  /api/v1/analytics/reviews
```

All mutation endpoints require:

- authentication
- authorization
- tenant context
- idempotency where relevant
- audit logging

---

# 11. Authentication

Recommended:

- Auth.js / Clerk / WorkOS depending enterprise strategy
- OIDC/SAML later for enterprise
- MFA enforced for privileged roles

For B2B enterprise, **WorkOS** is a strong option when SSO/SCIM become requirements.

Do not build enterprise identity protocols from scratch.

---

# 12. Secrets

Secrets must live in:

- cloud secret manager
- managed KMS-backed secret store

Examples:

- AWS Secrets Manager
- GCP Secret Manager
- Azure Key Vault
- Doppler / 1Password Secrets Automation

Store integration metadata in Postgres; store raw credentials/tokens only in the secret store.

---

# 13. Security architecture

Principles:

- tenant isolation
- least privilege
- OAuth token rotation
- signed webhook validation
- replay protection
- encryption at rest/in transit
- dependency scanning
- secret scanning
- audit logs
- immutable action history
- admin action logging

High-risk operations require policy evaluation.

---

# 14. Policy engine

Use deterministic policy rules.

Example:

```yaml
actions:
  github.merge_pr:
    approval: always

  github.comment:
    approval: policy

  jira.create_issue:
    approval: policy

  slack.post_message:
    approval: policy

  calendar.create_event:
    approval: policy
```

Policy evaluates:

- actor
- tenant
- resource
- action
- risk
- confidence
- workflow
- environment

---

# 15. Observability

Use OpenTelemetry.

Capture:

### Logs
- structured JSON
- correlation ID
- tenant ID
- mission ID
- action ID

### Metrics
- webhook latency
- model latency
- action failures
- queue depth
- review SLA metrics
- integration API error rates

### Traces
Trace:

`event → context retrieval → reasoning → proposal → approval → execution → verification`

Recommended stack:

- OpenTelemetry
- Prometheus
- Grafana
- Sentry

---

# 16. Environments

```text
local
development
staging
production
```

Production external integrations must never share credentials with development.

---

# 17. Deployment

Recommended for an initial startup:

### Frontend
Vercel or equivalent managed Next.js platform.

### Backend
AWS ECS/Fargate, Google Cloud Run, Azure Container Apps, or Kubernetes only when justified.

### Database
Managed PostgreSQL.

### Redis
Managed Redis.

### Object storage
S3-compatible storage.

### Temporal
Temporal Cloud initially; self-host later if warranted.

---

# 18. CI/CD

Pipeline:

```text
Pull Request
  ↓
Lint
  ↓
Typecheck
  ↓
Unit tests
  ↓
Integration tests
  ↓
Security scans
  ↓
Build
  ↓
Preview/staging
  ↓
E2E smoke tests
  ↓
Production deployment
```

Use:

- GitHub Actions
- Dependabot/Renovate
- secret scanning
- SAST
- container scanning

---

# 19. Testing strategy

## Unit tests

Business rules:

- routing
- risk signals
- SLA
- policy
- state transitions

## Integration tests

- GitHub API
- Slack API
- Calendar
- Jira/Linear
- Notion

Use contract fixtures and sandbox accounts.

## E2E

Critical journey:

`PR event → Context Pack → approval → Slack → calendar → verification`

## Agent evaluation

Maintain a fixed benchmark set of PR/missions and evaluate:

- evidence completeness
- action correctness
- hallucination rate
- routing quality
- risk classification
- policy violations

---

# 20. Performance targets

Initial targets:

- webhook acceptance < 2s
- PR ingestion < 10s
- initial Context Pack < 60s
- normal UI interaction < 200ms perceived response where cached
- dashboard first meaningful render < 2.5s on a normal broadband desktop
- action execution should provide progress feedback immediately

---

# 21. Cost control

Use model routing:

```text
Simple classification
    ↓
fast/cheap model

Complex synthesis
    ↓
strong model

Deterministic lookup
    ↓
no model
```

Cache:

- stable repository metadata
- project metadata
- user/team skills
- resolved links
- embeddings when applicable

Avoid sending full diffs to the model by default.

First retrieve relevant files, symbols, commits, and metadata.

---

# 22. Repository structure

```text
parallax/
├── apps/
│   ├── web/
│   ├── api/
│   └── workers/
├── packages/
│   ├── ui/
│   ├── config/
│   ├── db/
│   ├── auth/
│   ├── integrations/
│   ├── agent-core/
│   ├── policy/
│   ├── telemetry/
│   └── schemas/
├── workflows/
├── infra/
├── docs/
└── tests/
```

---

# 23. Engineering conventions

- TypeScript strict mode.
- Zod at trust boundaries.
- Typed integration contracts.
- Domain events for cross-module state changes.
- Idempotency keys on mutations.
- No hidden side effects inside read methods.
- No LLM calls from database-layer functions.
- No external API calls from pure domain logic.
- Centralized authorization.
- Explicit workflow state machines.

---

# 24. Architecture decision summary

| Decision | Recommendation |
|---|---|
| UI | Next.js + React + TypeScript |
| Backend | TypeScript + modular NestJS/Fastify |
| DB | PostgreSQL |
| Cache | Redis |
| Durable workflow | Temporal |
| AI graph | LangGraph-style explicit graph |
| Auth | Managed B2B identity |
| Events | Webhooks + outbox + workers |
| Search | Postgres/pgvector first |
| Observability | OpenTelemetry + Grafana + Sentry |
| Hosting | Managed cloud services |
| CI/CD | GitHub Actions |
| Testing | Vitest + Playwright |

The central architectural constraint is to keep **AI reasoning, policy, and execution separate**.