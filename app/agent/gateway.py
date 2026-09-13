from dataclasses import dataclass

import httpx
from pydantic import ValidationError

from app.agent.contracts import (
    AgentContextRequest,
    AgentContextResponse,
    validate_agent_evidence,
)
from app.agent.fallback import deterministic_response
from app.config import Settings, settings


@dataclass(frozen=True)
class AgentGatewayResult:
    response: AgentContextResponse
    mode: str
    fallback_reason: str | None = None


class AgentGateway:
    def __init__(
        self,
        config: Settings = settings,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.config = config
        self.client = httpx.AsyncClient(
            base_url=config.agent_service_url.rstrip("/"),
            timeout=config.agent_timeout_seconds,
            headers={
                "Authorization": f"Bearer {config.agent_service_api_key.get_secret_value()}",
                "Content-Type": "application/json",
            },
            transport=transport,
        )

    async def analyze(self, request: AgentContextRequest) -> AgentGatewayResult:
        if self.config.agent_mode == "fallback":
            return self._fallback(request, "AGENT_MODE=fallback")
        try:
            response = await self.client.post("/v1/analyze", json=request.model_dump(mode="json"))
            response.raise_for_status()
            parsed = AgentContextResponse.model_validate(response.json())
            validate_agent_evidence(parsed, {item.key for item in request.evidence})
            return AgentGatewayResult(response=parsed, mode="service")
        except (httpx.HTTPError, ValueError, ValidationError) as exc:
            if not self.config.agent_fallback_enabled:
                raise RuntimeError("Agent service response failed validation") from exc
            return self._fallback(request, type(exc).__name__)

    def _fallback(self, request: AgentContextRequest, reason: str) -> AgentGatewayResult:
        response = deterministic_response(request)
        validate_agent_evidence(response, {item.key for item in request.evidence})
        return AgentGatewayResult(response=response, mode="fallback", fallback_reason=reason)

    async def close(self) -> None:
        await self.client.aclose()
