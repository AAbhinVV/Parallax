import uuid
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

from parallax_backend.models import IntegrationProvider


class AgentEvidence(BaseModel):
    key: str
    provider: IntegrationProvider
    external_id: str
    title: str
    url: str | None = None
    excerpt: str


class AgentContextRequest(BaseModel):
    contract_version: Literal["1.0"] = "1.0"
    mission_id: uuid.UUID
    prompt: str
    project: str
    context_summary: str
    evidence: list[AgentEvidence]
    # Additive, v1.0-compatible: mission knowledge base excerpt assembled by
    # the backend (latest verified facts, decisions, action outcomes, conflicts).
    # The agent must ground its output in evidence citations; knowledge_base
    # entries are operational context, not a replacement for fresh verification.
    knowledge_base: dict[str, Any] | None = None


class RiskAssessment(BaseModel):
    level: Literal["low", "medium", "high", "critical"]
    factors: list[str] = Field(min_length=1, max_length=20)
    citations: list[str] = Field(min_length=1)


class EffortAssessment(BaseModel):
    minutes: int = Field(ge=5, le=2400)
    rationale: str = Field(min_length=3, max_length=2000)
    citations: list[str] = Field(min_length=1)


class ReviewerCandidate(BaseModel):
    identity: str = Field(min_length=1, max_length=255)
    score: float = Field(ge=0, le=1)
    reason: str = Field(min_length=3, max_length=2000)
    citations: list[str] = Field(min_length=1)


class AgentProposal(BaseModel):
    provider: IntegrationProvider
    operation: str = Field(min_length=3, max_length=120)
    rationale: str = Field(min_length=3, max_length=2000)
    payload: dict[str, Any] = Field(default_factory=dict)
    citations: list[str] = Field(min_length=1)


class AgentContextResponse(BaseModel):
    contract_version: Literal["1.0"] = "1.0"
    context_summary: str = Field(min_length=3, max_length=5000)
    risk: RiskAssessment
    effort: EffortAssessment
    reviewer_candidates: list[ReviewerCandidate] = Field(min_length=1, max_length=20)
    confidence: float = Field(ge=0, le=1)
    explanation: str = Field(min_length=3, max_length=5000)
    citations: list[str] = Field(min_length=1)
    proposals: list[AgentProposal] = Field(max_length=50)

    @field_validator("citations")
    @classmethod
    def unique_citations(cls, value: list[str]) -> list[str]:
        if len(value) != len(set(value)):
            raise ValueError("Citations must be unique")
        return value


ALLOWED_PROPOSALS: dict[IntegrationProvider, frozenset[str]] = {
    IntegrationProvider.GITHUB: frozenset(),
    IntegrationProvider.JIRA: frozenset({"issue.create", "issue.update"}),
    IntegrationProvider.NOTION: frozenset({"page.append"}),
    IntegrationProvider.SLACK: frozenset({"message.post", "message.update"}),
}


def validate_agent_evidence(response: AgentContextResponse, evidence_keys: set[str]) -> None:
    cited = set(response.citations)
    cited.update(response.risk.citations)
    cited.update(response.effort.citations)
    for reviewer in response.reviewer_candidates:
        cited.update(reviewer.citations)
    for proposal in response.proposals:
        cited.update(proposal.citations)
        if proposal.operation not in ALLOWED_PROPOSALS[proposal.provider]:
            raise ValueError(f"Unsupported proposal {proposal.provider.value}:{proposal.operation}")
    unknown = cited - evidence_keys
    if unknown:
        raise ValueError(f"Agent response cites unknown evidence: {sorted(unknown)}")
