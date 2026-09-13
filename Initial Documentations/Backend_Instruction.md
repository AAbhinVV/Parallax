You are a senior Backend developer who is assigned to make a project Called Parallax:

My understanding of Parallax:

- It is an **engineering operations control plane**, not an AI code reviewer or chatbot.
- Its initial wedge is **PR triage and review orchestration**: build context, assess risk and effort, select reviewers, find availability, request review, track SLAs, and expose review debt.
- Its defining workflow is:

  `Observe → Contextualize → Reason → Propose → Critique → Policy → Approval → Execute → Verify → Record`

- AI handles synthesis and judgment; deterministic systems handle policy, permissions, execution, verification, and auditability.
- Connected products—GitHub, Slack, Jira/Linear, Notion, and Google Calendar—remain the systems of record.
- The proposed architecture is a TypeScript modular monolith with Next.js, PostgreSQL, Redis, explicit workflow state machines, and eventually Temporal for durable missions.
- The product experience is a dense, premium control-room dashboard centered on a dominant mission command surface—not a chat-first interface.
- The roadmap sensibly moves from platform foundations to PR intelligence, review orchestration, general missions, and predictive operations.

The documents are unusually aligned across product, engineering, agent behavior, and design. The most important decisions still open are:

- How narrowly to scope the first genuinely shippable version
- Jira versus Linear for the initial project-management integration
- When Temporal becomes necessary
- How reviewer expertise and fairness are initialized for new teams
- Calendar privacy and whether proposed blocks are tentative or confirmed
- Risk-score calibration and explainability
- Cross-tool user/entity identity mapping
- Exact permission defaults for Slack and Calendar writes

The main product risk I see is **MVP breadth**: the stated MVP already combines five integrations, contextual retrieval, risk analysis, reviewer routing, scheduling, approvals, audit, verification, SLA tracking, and analytics. The vision is coherent, but the first release may need a tighter vertical slice to reach trustworthy production quality.

I’m fully oriented and ready to discuss whichever dimension you want first—product scope, architecture, UX, agent design, or implementation strategy.


This is a project's backend:

Anshumaan657: Extract all the necessary deatils from this .md fils as Backend developer.

Workspace: Collecting workspace informationAs a backend developer, the following details extracted from the TECH_STACK.md file are relevant for building and maintaining the backend of the Parallax project:

---

### **Backend Architecture**
- **Language/Runtime**: TypeScript, Node.js runtime.
- **Frameworks**: 
  - NestJS (preferred) or modular Fastify-based application.
  - tRPC for internal typed APIs.
- **API Design**:
  - REST/Webhooks for external integrations.
  - OpenAPI for public/internal boundary documentation.
- **Architecture Style**: Modular monolith for the first production release with explicit domain modules.

---

### **Core Backend Modules**
- `/auth`
- `/tenancy`
- users
- `/teams`
- `/integrations`
- `/events`
- `/github`
- `/slack`
- `/jira`
- `/linear`
- `/notion`
- `/calendar`
- `/pr-intelligence`
- `/context-packs`
- `/risk`
- `/reviewer-routing`
- `/scheduling`
- `/missions`
- `/planner`
- `/policy`
- `/approvals`
- `/execution`
- `/verification`
- `/audit`
- `/analytics`
- `/notifications`

Each module owns its domain logic and exposes stable internal interfaces.

---

### **Data Layer**
- **Primary Database**: PostgreSQL.
  - Use for tenants, users, teams, integrations, repository metadata, PR metadata, context packs, reviewer assignments, missions, action proposals, approvals, execution records, audit records, and analytics aggregates.
  - Use row-level security only where it provides additional defense.
- **Cache/Ephemeral State**: Redis.
  - Use for rate limits, short-lived locks, job state, deduplication windows, session-adjacent ephemeral data, and frequently requested computed views.
  - Do not use Redis as the system of record.
- **Search**:
  - Start with PostgreSQL full-text + `pgvector` if required.
  - Introduce OpenSearch only when:
    - Audit/activity search becomes large.
    - Cross-document search requirements exceed PostgreSQL.
    - Operational logs need a dedicated search plane.
- **Object Storage**: S3-compatible storage.
  - Use for exported reports, large evidence artifacts, optional model inputs/outputs, and retained snapshots where policy permits.

---

### **Eventing and Jobs**
- **Recommended Approach**:
  - Postgres-backed outbox.
  - Durable job queue.
  - Redis-based workers or managed queue.
  - Webhook ingestion endpoint.
- **Candidate Platforms**:
  - BullMQ.
  - Trigger.dev.
  - Temporal (recommended for complex durable workflows).
- **Temporal Use Case**:
  - Multi-step execution involving pauses for approval, retries, external APIs, timers, escalations, human tasks, and long-running execution.

---

### **Authentication**
- **Recommended Tools**:
  - Auth.js / Clerk / WorkOS depending on enterprise strategy.
  - OIDC/SAML for enterprise later.
  - MFA enforced for privileged roles.
- **B2B Enterprise Recommendation**:
  - WorkOS for SSO/SCIM requirements.
- **Guidance**:
  - Do not build enterprise identity protocols from scratch.

---

### **Secrets Management**
- **Storage Options**:
  - Cloud secret manager.
  - Managed KMS-backed secret store.
- **Examples**:
  - AWS Secrets Manager.
  - GCP Secret Manager.
  - Azure Key Vault.
  - Doppler / 1Password Secrets Automation.
- **Guidance**:
  - Store integration metadata in PostgreSQL.
  - Store raw credentials/tokens only in the secret store.

---

### **Security Architecture**
- **Principles**:
  - Tenant isolation.
  - Least privilege.
  - OAuth token rotation.
  - Signed webhook validation.
  - Replay protection.
  - Encryption at rest/in transit.
  - Dependency scanning.
  - Secret scanning.
  - Audit logs.
  - Immutable action history.
  - Admin action logging.
- **High-Risk Operations**:
  - Require policy evaluation.

---

### **Policy Engine**
- **Rules**:
  - Use deterministic policy rules.
- **Example**:
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
- **Policy Evaluates**:
  - Actor, tenant, resource, action, risk, confidence, workflow, and environment.

---

### **Observability**
- **Recommended Stack**:
  - OpenTelemetry.
  - Prometheus.
  - Grafana.
  - Sentry.
- **Capture**:
  - **Logs**: Structured JSON, correlation ID, tenant ID, mission ID, action ID.
  - **Metrics**: Webhook latency, model latency, action failures, queue depth, review SLA metrics, integration API error rates.
  - **Traces**: Event → context retrieval → reasoning → proposal → approval → execution → verification.

---

### **Environments**
- **Defined Environments**:
  - `local`, `development`, `staging`, `production`.
- **Guidance**:
  - Production external integrations must never share credentials with development.

---

### **Deployment**
- **Recommended Platforms**:
  - **Frontend**: Vercel or equivalent managed Next.js platform.
  - **Backend**: AWS ECS/Fargate, Google Cloud Run, Azure Container Apps, or Kubernetes (only when justified).
  - **Database**: Managed PostgreSQL.
  - **Redis**: Managed Redis.
  - **Object Storage**: S3-compatible storage.
  - **Temporal**: Temporal Cloud initially; self-host later if warranted.

---

### **CI/CD**
- **Pipeline**:
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
- **Tools**:
  - GitHub Actions.
  - Dependabot/Renovate.
  - Secret scanning.
  - SAST.
  - Container scanning.

---

### **Testing Strategy**
- **Unit Tests**:
  - Business rules: routing, risk signals, SLA, policy, state transitions.
- **Integration Tests**:
  - GitHub API, Slack API, Calendar, Jira/Linear, Notion.
  - Use contract fixtures and sandbox accounts.
- **E2E Tests**:
  - Critical journey: `PR event → Context Pack → approval → Slack → calendar → verification`.
- **Agent Evaluation**:
  - Maintain a fixed benchmark set of PR/missions and evaluate:
    - Evidence completeness.
    - Action correctness.
    - Hallucination rate.
    - Routing quality.
    - Risk classification.
    - Policy violations.

---

### **Performance Targets**
- **Initial Targets**:
  - Webhook acceptance < 2s.
  - PR ingestion < 10s.
  - Initial Context Pack < 60s.
  - Normal UI interaction < 200ms perceived response where cached.
  - Dashboard first meaningful render < 2.5s on a normal broadband desktop.
  - Action execution should provide progress feedback immediately.

---

### **Repository Structure**
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

### **Engineering Conventions**
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

### **Architecture Decision Summary**
| Decision          | Recommendation                     |
|-------------------|-------------------------------------|
| **Backend**       | TypeScript + modular NestJS/Fastify|
| **DB**            | PostgreSQL                        |
| **Cache**         | Redis                             |
| **Durable Workflow** | Temporal                       |
| **Auth**          | Managed B2B identity              |
| **Events**        | Webhooks + outbox + workers       |
| **Search**        | Postgres/pgvector first           |
| **Observability** | OpenTelemetry + Grafana + Sentry  |
| **Hosting**       | Managed cloud services            |
| **CI/CD**         | GitHub Actions                    |
| **Testing**       | Vitest + Playwright               |

---

This information provides a comprehensive guide for backend development in the Parallax project.

Anshumaan657: @GitHubCopilot 