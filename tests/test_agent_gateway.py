import json
import uuid
from typing import cast

import httpx
import pytest

from parallax_backend.agent.contracts import (
    AgentContextRequest,
    AgentContextResponse,
    AgentEvidence,
    validate_agent_evidence,
)
from parallax_backend.agent.gateway import AgentGateway
from parallax_backend.config import Settings
from parallax_backend.models import IntegrationProvider


def request_contract() -> AgentContextRequest:
    return AgentContextRequest(
        mission_id=uuid.uuid4(),
        prompt="Review the payments change",
        project="Payments",
        context_summary="One GitHub pull request was collected.",
        evidence=[
            AgentEvidence(
                key="github:pull_request:7",
                provider=IntegrationProvider.GITHUB,
                external_id="7",
                title="Payments change",
                excerpt="Changes payment authorization handling",
            )
        ],
    )


def response_payload(citation: str = "github:pull_request:7") -> dict[str, object]:
    return {
        "contract_version": "1.0",
        "context_summary": "The payment change needs review.",
        "risk": {"level": "high", "factors": ["Payment path"], "citations": [citation]},
        "effort": {"minutes": 45, "rationale": "Focused change", "citations": [citation]},
        "reviewer_candidates": [
            {
                "identity": "payments-maintainer",
                "score": 0.9,
                "reason": "Owns the affected area",
                "citations": [citation],
            }
        ],
        "confidence": 0.85,
        "explanation": "Evidence supports a focused high-risk review.",
        "citations": [citation],
        "proposals": [
            {
                "provider": "slack",
                "operation": "message.post",
                "rationale": "Request review after approval",
                "payload": {"text": "Please review"},
                "citations": [citation],
            }
        ],
    }


def service_settings(*, fallback: bool = True) -> Settings:
    return Settings(
        agent_mode="service",
        agent_service_url="https://agent.example",
        agent_service_api_key="agent-secret",
        agent_fallback_enabled=fallback,
    )


@pytest.mark.asyncio
async def test_gateway_accepts_typed_evidence_backed_service_response() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/analyze"
        body = json.loads(request.content)
        assert body["contract_version"] == "1.0"
        assert body["evidence"][0]["key"] == "github:pull_request:7"
        assert request.headers["authorization"] == "Bearer agent-secret"
        return httpx.Response(200, json=response_payload())

    gateway = AgentGateway(service_settings(), httpx.MockTransport(handler))
    try:
        result = await gateway.analyze(request_contract())
        assert result.mode == "service"
        assert result.response.risk.level == "high"
    finally:
        await gateway.close()


@pytest.mark.asyncio
async def test_invalid_agent_citation_uses_deterministic_fallback() -> None:
    gateway = AgentGateway(
        service_settings(),
        httpx.MockTransport(lambda _: httpx.Response(200, json=response_payload("unknown:item"))),
    )
    try:
        result = await gateway.analyze(request_contract())
        assert result.mode == "fallback"
        assert result.fallback_reason == "ValueError"
        assert result.response.confidence == 0.55
    finally:
        await gateway.close()


@pytest.mark.asyncio
async def test_invalid_agent_response_fails_when_fallback_disabled() -> None:
    gateway = AgentGateway(
        service_settings(fallback=False),
        httpx.MockTransport(lambda _: httpx.Response(200, json=response_payload("unknown:item"))),
    )
    try:
        with pytest.raises(RuntimeError, match="failed validation"):
            await gateway.analyze(request_contract())
    finally:
        await gateway.close()


def test_validator_rejects_unsupported_action() -> None:
    payload = response_payload()
    proposals = cast(list[dict[str, object]], payload["proposals"])
    proposals[0]["provider"] = "github"
    response = AgentContextResponse.model_validate(payload)
    with pytest.raises(ValueError, match="Unsupported proposal"):
        validate_agent_evidence(response, {"github:pull_request:7"})
