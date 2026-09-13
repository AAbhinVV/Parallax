from app.agent.contracts import (
    AgentContextRequest,
    AgentContextResponse,
    AgentProposal,
    EffortAssessment,
    ReviewerCandidate,
    RiskAssessment,
)
from app.models import IntegrationProvider


def deterministic_response(request: AgentContextRequest) -> AgentContextResponse:
    evidence_keys = [item.key for item in request.evidence]
    citation = evidence_keys[0]
    prompt = request.prompt.lower()
    high_signal = any(word in prompt for word in ("security", "payment", "migration", "incident"))
    risk_level = "high" if high_signal else "medium"
    effort = min(240, max(30, len(request.evidence) * 15))
    proposals: list[AgentProposal] = []
    if any(item.provider == IntegrationProvider.JIRA for item in request.evidence):
        proposals.append(
            AgentProposal(
                provider=IntegrationProvider.JIRA,
                operation="issue.create",
                rationale="Keep the linked delivery record synchronized after approval",
                payload={
                    "fields": {
                        "project": {"key": request.project.upper().replace(" ", "-")},
                        "summary": request.prompt[:160],
                        "issuetype": {"name": "Task"},
                    }
                },
                citations=[citation],
            )
        )
    proposals.append(
        AgentProposal(
            provider=IntegrationProvider.SLACK,
            operation="message.post",
            rationale="Notify the project channel after approval",
            payload={"text": f"Review requested for {request.project}: {request.prompt[:300]}"},
            citations=[citation],
        )
    )
    return AgentContextResponse(
        context_summary=request.context_summary,
        risk=RiskAssessment(
            level=risk_level,
            factors=["Deterministic assessment based on mission scope and collected evidence"],
            citations=[citation],
        ),
        effort=EffortAssessment(
            minutes=effort,
            rationale="Estimated from the number of available cross-tool evidence items",
            citations=[citation],
        ),
        reviewer_candidates=[
            ReviewerCandidate(
                identity="project-maintainer",
                score=0.65,
                reason="Deterministic fallback selects the configured project maintainer role",
                citations=[citation],
            )
        ],
        confidence=0.55,
        explanation=(
            "The Agent service was bypassed or unavailable, so Parallax generated a conservative "
            "deterministic assessment. Every conclusion remains tied to collected evidence."
        ),
        citations=evidence_keys,
        proposals=proposals,
    )
