# Parallax Backend (FastAPI Control Plane)

API/control-plane layer. All mission planning, approval gating,
authorized execution, verification and auditability live in
**Agent Core** (`packages/agent-core`, LangGraph, port `:4010`).
This backend only validates requests, forwards missions to
Agent Core, and relays state/decisions.

```
FastAPI Backend  (this package, port 8000)
       |
       v
POST /missions
       |
       v
Agent Core :4010  (LangGraph orchestration)
```

## Setup

```bash
cd packages/backend
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt
```

## Run

```bash
# 1. Start Agent Core (in packages/agent-core)
npm run server

# 2. Start the backend
uvicorn app.main:app --reload --port 8000
```

Configuration (env vars):

| Variable | Default | Purpose |
|---|---|---|
| `AGENT_CORE_URL` | `http://localhost:4010` | Agent Core base URL |
| `AGENT_CORE_TIMEOUT_SECONDS` | `120` | Timeout for Agent Core calls |

## API

| Method | Path | Description |
|---|---|---|
| GET | `/health` | Liveness + Agent Core URL |
| POST | `/api/v1/missions` | Start a mission (`{mission}`); the backend generates the mission ID (uuid4) |
| GET | `/api/v1/missions/{id}` | Normalized mission status incl. `currentStep` and `progress` (%) |
| POST | `/api/v1/missions/{id}/approve` | Approve the pending mission; Agent Core resumes the same thread |
| POST | `/api/v1/missions/{id}/reject` | Reject the pending mission |

Mission statuses: `planning`, `waiting_for_approval`, `running`,
`completed`, `partially_complete`, `failed`, `rejected`.

## Tests

```bash
pytest
```

Tests are hermetic — Agent Core is simulated with `httpx.MockTransport`,
so no server or credentials are needed.
