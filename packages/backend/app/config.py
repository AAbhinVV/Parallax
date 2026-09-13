"""Backend configuration for the Parallax control plane."""

import os

# Agent Core HTTP server (LangGraph orchestration layer).
AGENT_CORE_URL = os.environ.get("AGENT_CORE_URL", "http://localhost:4010")

# HTTP timeout for Agent Core calls. Missions can take a while
# because they invoke LLM reasoning and external tools.
AGENT_CORE_TIMEOUT_SECONDS = float(
    os.environ.get("AGENT_CORE_TIMEOUT_SECONDS", "120"),
)
