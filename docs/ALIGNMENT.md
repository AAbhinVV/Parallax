# Backend Alignment Decision

## Sources reviewed

- Shared Drive root prototype (`app/`, root README, dependencies)
- Shared Drive current `parallax-mvp/` backend and frontend
- Local PRD, agent flow, backend instructions, design, pipeline, and roadmap
- User decisions: manual mission input, local/self-hosted runtime, four integrations, and separate backend/agent teams

## Authoritative interpretation

The Drive contains two prototypes:

1. The root prototype is an older, GitHub-webhook-first PR triage demo using FastAPI, LlamaIndex, and Anthropic.
2. `parallax-mvp/` is the newer manual-mission console using FastAPI, LlamaIndex, Gemini, and the four required integrations.

For this backend, the newer manual-mission flow and the user's later scope decisions take precedence. The older webhook flow is not copied into the active API.

## Corrections made

- Replaced TypeScript/Fastify with Python FastAPI to match the Drive project and frontend.
- Changed the API port and compatibility health path to `8000` and `/api/health`.
- Kept PostgreSQL instead of the Drive demo's SQLite because missions, approvals, evidence, and audit records need a durable relational system of record.
- Kept Redis and a separate worker instead of FastAPI `BackgroundTasks`; long missions and retries must survive API request completion.
- Kept Prometheus and structured JSON logs for local visibility.
- Preserved GitHub, Jira, Notion, and Slack configuration; Calendar and GitHub webhooks are outside current scope.
- Did not embed the Drive's LlamaIndex agent in the backend. The agent team owns reasoning; the backend owns validated inputs/outputs, policy, approval, execution, verification, and audit.

## Team contracts

### Frontend

Frontend calls only versioned FastAPI routes and consumes the committed OpenAPI contract. The backend supplies mission polling, dashboard data, integration status, action previews, approval state, and execution history. Mock/seed endpoints will keep frontend work independent of live integrations.

### Agent

Backend sends a typed, read-only context request containing mission scope and evidence references. Agent returns structured analysis, confidence, citations, and typed proposed actions. Agent code never receives connector write credentials and never executes Slack, Jira, Notion, or GitHub mutations.

### Deployment and testing

The complete system runs with Docker Compose on the developer machine. This team owns local environment setup, credentials, CI, seeded demo data, smoke tests, failure visibility, and reset/backup scripts. No cloud hosting is required.

## Target execution flow

```text
Manual mission
  → FastAPI validation and persistence
  → Redis job
  → worker gathers GitHub/Jira/Notion context
  → backend sends typed context to Agent service
  → backend validates proposed actions and policy
  → frontend approval/edit/reject/cancel
  → worker executes approved actions
  → worker reads integrations back to verify
  → PostgreSQL audit/timeline/dashboard records
```

