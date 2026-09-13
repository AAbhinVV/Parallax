
# Parallax — Persistent Operational Agent

Parallax is a **single-agent operational system**: one agent reasons over grounded
cross-tool context, proposes actions, and executes a durable multi-step workflow
through real integrations — with every mutation policy-gated, human-approved, and
verified against the external system before it counts as done.

It combines ideas from two open-source architectures:

- **Omni-style** — *understand the world*: connectors, evidence collection with
  provenance, persistent knowledge, citation-grounded reasoning
- **Apteva-style** — *own the work*: durable missions, persistent step state,
  worker leases, crash recovery, retry/resume, event-driven wake-up

…and adds Parallax's differentiator: **controlled reasoning** — schema-validated
decisions, deterministic policy, human approval, read-after-write verification,
and completion that requires evidence.

## The problem it solves

Typical LLM agent workflows fail in predictable ways:

| Failure mode | Parallax's answer |
|---|---|
| Agent re-executes work that was already done | Task fingerprint + completion proof → duplicate missions return the existing verified result, no re-execution |
| Agent claims success without evidence | No verified completion → no "done"; every action is read back from the external system |
| Worker crash loses progress | DB-persisted step state + leases; a new worker resumes, skipping verified actions |
| Replayed webhooks duplicate actions | Stable event identity + dedup; replays never route twice |
| Agent hallucinates tickets, people, or actions | Model output is a *candidate*: schema-validated, citations checked against collected evidence, operations restricted per provider |
| Model drifts into unrelated operations | One canonical system prompt; task-driven reasoning; GitHub is read-only by harness design |

## What was built

- **Reasoning layer** (TypeScript/LangGraph/Gemini) — one canonical reasoning path
  shared by every interface; flat `MissionContext` wire contract; structured JSON
  output (`action_required | already_completed | needs_clarification |
  no_action_required`) with confidence, uncertainties, and evidence citations
- **Agent harness** (FastAPI backend) — deterministic, non-LLM control: task
  identity (SHA-256 fingerprint), duplicate/resume resolution, completion proofs,
  worker leases, retry classification, event routing
- **Knowledge base** — append-only facts (`source_fact` vs `decision`), automatic
  superseding, verified-first bounded context packs with provenance
- **Durable mission runtime** — step state, lease claim/renew/release, crash
  recovery at worker startup, retry/resume without re-running verified work
- **Event router + webhooks** — `POST /api/webhooks/{provider}` wakes affected
  missions (`WAITING_FOR_EVENT → RUNNING`); replay-safe
- **Context engine seam** — two-stage retrieval (exact entity match → text match)
  over the knowledge base, ready for BM25/pgvector without changing the agent
- **Connector capability registry** — harness-enforced boundaries: GitHub
  read/write ✗, verify ✓; Jira/Slack/Notion fully mutation-capable

## External apps (4 connected)

| System | Read | Write | Verify | Role |
|---|:---:|:---:|:---:|---|
| **Jira** (REST) | ✓ | ✓ | ✓ | project-management actions (create/update issues) |
| **Slack** (REST) | ✓ | ✓ | ✓ | team notifications (post/update messages) |
| **Notion** (REST) | ✓ | ✓ | ✓ | documentation & memory (page read/append) |
| **GitHub** (MCP) | ✓ | ✗ | ✓ | source/context only — writes deliberately rejected |

Every write is followed by a **read-after-write verification**: the action only
counts as `verified` when the external system confirms the new state.

## Architecture

```text
              PM / EVENT
                  │
                  ▼
             Mission API
                  │
        Task Identity + Duplicate Check
                  │
                  ▼
          ┌───────────────┐        ┌────────────────┐
          │ CONTEXT ENGINE│        │ MISSION RUNTIME│
          │ connectors    │        │ leases / steps │
          │ exact+text    │        │ retry / resume │
          │ provenance    │        │ wait / wake    │
          └───────┬───────┘        └────────┬───────┘
                  └──────────┬───────────────┘
                             ▼
                 Gemini + LangGraph (one agent)
                             ▼
                    Plan / Policy / Approval
                             ▼
                  Durable Execute (connectors)
                             ▼
              Verify (read-after-write) ──✗──▶ retry / resume
                             ▼
                Completion Proof + Knowledge Base
                             ▼
                     Timeline / Audit / API
                             ▲
                             │
                     Event Router (webhooks)
```

## Setup

### Prerequisites

- Python 3.10+
- Node.js 18+
- Docker (Redis; GitHub MCP server)
- A Gemini API key, plus Jira / Slack / Notion / GitHub credentials

### Install

```bash
git clone https://github.com/AAbhinVV/Parallax.git
cd Parallax

# Backend (Python)
python -m venv .venv
.venv\Scripts\activate            # Windows  (source .venv/bin/activate on macOS/Linux)
pip install -r requirements.txt

# Agent Core (TypeScript)
cd packages\agent-core
npm install
cd ..\..
```

### Configure

```bash
copy .env.example .env            # cp .env.example .env on macOS/Linux
```



### Database

```bash
# Fastest demo (SQLite):
python create_demo_db.py

# Production-like (PostgreSQL):
#   set DATABASE_URL=postgresql+asyncpg://... in .env, then:
alembic upgrade head
```

### Run

Terminal 1 — Agent Core (`:4010`):

```bash
cd packages\agent-core
npm run server
```

Terminal 2 — Redis:

```bash
docker run --name parallax-redis -p 6379:6379 -d redis:7
```

Terminal 3 — Backend API (`:8000`, docs at `/docs`):

```bash
uvicorn app.main:app --port 8000
```

Terminal 4 — Worker (mission execution, leases, recovery, retries, outbox):

```bash
arq app.worker.WorkerSettings
```

On startup the worker performs expired-lease recovery and logs
`recovered_missions=N`.

## How it is tested

### Automated suites

```bash
# Backend — control plane, harness, runtime, event router (64 tests)
.venv\Scripts\python.exe -m pytest tests
# Type safety
.venv\Scripts\python.exe -m mypy app

# Agent Core — reasoning layer (43 tests)
cd packages\agent-core
npm test
npm run typecheck
```

### Reliability testing (the durable-runtime proof)

The acceptance test for crash recovery runs the exact production path:

1. Approve a mission whose plan contains a Jira action and a Slack action
2. Inject a transient Slack failure → mission ends `partially_complete`
3. Simulate a worker crash: the lease expires, `recover_expired_missions()`
   clears it and requeues the mission
4. A new worker claims it: **the verified Jira action is skipped (attempt count
   unchanged)**, the failed Slack action is retried, mission ends `completed`
5. Completion proof is written from verified execution records only

Tested in `tests/test_mission_runtime.py`; duplicate prevention in
`tests/test_task_identity.py`; event replay-safety in `tests/test_event_router.py`.

### Verify it live

```bash
# 1. Submit a mission (reasoning fires: gateway → /v1/analyze → Gemini)
curl -X POST http://localhost:8000/api/missions ...
# 2. Inspect the validated assessment and grounded context
curl http://localhost:8000/api/missions/{id}/assessment
curl http://localhost:8000/api/missions/{id}/context-pack
# 3. Approve, then watch durable execution + verification + proof
curl http://localhost:8000/api/missions/{id}/executions   # every action verified
# 4. Submit the same mission again → returns the existing completed mission,
#    no duplicate actions
# 5. Wake a parked mission through a webhook
curl -X POST http://localhost:8000/api/webhooks/jira -d "{\"event_type\":\"issue_updated\",\"external_id\":\"PAY-18\"}"
```

### The guarantee

> **LLM output ≠ system truth.** The model proposes; the backend disposes.
> Operations are restricted per provider, citations must map to actually
> collected evidence, mutations require approval, results require read-back
> verification, and completion requires proof. If a worker dies, verified work
> is never repeated — and an already-verified objective is never executed twice.
=======
# Parallax

Parallax is a locally runnable engineering workflow platform. The Next.js
frontend submits missions to a FastAPI control plane, an ARQ worker gathers
context and coordinates planning, and the TypeScript Agent service provides
structured reasoning. PostgreSQL stores application and audit data, Redis
backs the worker queue, and Prometheus collects API metrics.

## Local stack

Requirements: Docker Desktop with Compose v2. No vendor credentials are
required in the default mock/fallback configuration.

```bash
cp .env.example .env
docker compose up --build -d
docker compose ps
```

Open the services at:

- Frontend: http://localhost:3000
- FastAPI/OpenAPI: http://localhost:8000/docs
- Agent health: http://localhost:8100/health
- Prometheus: http://localhost:9090

Check readiness and logs:

```bash
curl -fsS http://localhost:8000/ready
curl -fsS http://localhost:8100/health
curl -fsS http://localhost:3000/login
docker compose logs --tail=100 api worker agent frontend
```

Stop the stack with `docker compose down`. Add `-v` only when you intentionally
want to delete local PostgreSQL, Redis, and Prometheus data.

## Development checks

```bash
npm ci
npm run api:check
npm run typecheck
npm run lint
npm test
npm run build

(cd packages/agent-core && npm ci && npm run typecheck && npm test && npm run build)

ruff check parallax_backend tests scripts migrations
ruff format --check parallax_backend tests scripts migrations
mypy parallax_backend scripts
pytest tests
alembic check
```

The API contract used by the frontend is [docs/openapi.json](docs/openapi.json),
with a human-readable endpoint guide in [docs/API.md](docs/API.md).

## Configuration

Keep `.env` local and secret. The committed `.env.example` contains names and
safe placeholders only. `INTEGRATION_MODE=mock` prevents writes to GitHub,
Jira, Notion, and Slack. `AGENT_MODE=fallback` uses deterministic planning;
Docker Compose overrides it to `service` and safely falls back if the Agent or
model is unavailable. Configure real vendor credentials only in a secret
manager or an untracked `.env`.
