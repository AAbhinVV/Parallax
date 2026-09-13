import type { ModelGateway } from "./model-gateway.js";
import {
  renderEvidenceBlocks,
  reasonOverMission,
  type EvidenceBlock,
} from "./reason.js";
import type { PolicyRecommendation } from "../schemas/policy-recommendation.js";
import type { MissionContext } from "../types/mission-context.js";

/*
 * K2.8 boundary: the backend's real /v1/analyze contract.
 *
 * The backend posts an AgentContextRequest (prompt + knowledge_base +
 * collected evidence). We run the single reasoning path over it and
 * translate the model's structured decision into the AgentContextResponse
 * the backend validates.
 *
 * Anti-hallucination invariants enforced here (mirrored by the backend's
 * validate_agent_evidence):
 * - every citation is one of the request's evidence keys
 * - proposals only use operations the backend allows for their provider
 * - reasoning drives WHETHER to act (status); the structured, safety-
 *   sensitive fields (risk / effort / reviewer identity) are assembled
 *   deterministically so the model never invents people or scores.
 */

export type AgentEvidence = {
  key: string;
  provider: string;
  external_id: string;
  title: string;
  url?: string | null;
  excerpt: string;
};

export type AgentContextRequestBody = {
  contract_version?: string;
  mission_id: string;
  prompt: string;
  project: string;
  context_summary: string;
  evidence: AgentEvidence[];
  knowledge_base?: MissionContext | null;
};

export type RiskAssessment = {
  level: "low" | "medium" | "high" | "critical";
  factors: string[];
  citations: string[];
};

export type EffortAssessment = {
  minutes: number;
  rationale: string;
  citations: string[];
};

export type ReviewerCandidate = {
  identity: string;
  score: number;
  reason: string;
  citations: string[];
};

export type AgentProposal = {
  provider: string;
  operation: string;
  rationale: string;
  payload: Record<string, unknown>;
  citations: string[];
};

export type AgentContextResponseBody = {
  contract_version: "1.0";
  context_summary: string;
  risk: RiskAssessment;
  effort: EffortAssessment;
  reviewer_candidates: ReviewerCandidate[];
  confidence: number;
  explanation: string;
  citations: string[];
  proposals: AgentProposal[];
};

/** Provider -> allowed operations, mirroring the backend ALLOWED_PROPOSALS. */
const ALLOWED_PROPOSALS: Record<string, ReadonlySet<string>> = {
  github: new Set<string>(),
  jira: new Set(["issue.create", "issue.update"]),
  notion: new Set(["page.append"]),
  slack: new Set(["message.post", "message.update"]),
};

const HIGH_SIGNAL = /security|payment|migration|incident/i;

function bounded(
  value: string,
  min: number,
  max: number,
  fallback: string,
): string {
  const trimmed = (value ?? "").trim();
  const safe = trimmed.length >= min ? trimmed : fallback;

  return safe.slice(0, max);
}

function buildProposals(
  request: AgentContextRequestBody,
  parsed: PolicyRecommendation,
  baseCitation: string,
): AgentProposal[] {
  // No verified action to take -> propose nothing (already_completed,
  // needs_clarification, no_action_required). This is the bridge toward
  // duplicate-task suppression: the reasoning layer can decline to act.
  if (parsed.status !== "action_required") {
    return [];
  }

  const proposals: AgentProposal[] = [];
  const prompt = request.prompt.toLowerCase();

  const wantsJira =
    request.evidence.some((item) => item.provider === "jira") ||
    /jira|issue|ticket|task/.test(prompt);
  if (wantsJira) {
    proposals.push({
      provider: "jira",
      operation: "issue.create",
      rationale: bounded(
        parsed.rationale,
        3,
        2000,
        "Create the tracking issue for the approved action.",
      ),
      payload: {
        fields: {
          project: {
            key: request.project.toUpperCase().replace(/\s+/g, "-"),
          },
          summary: (parsed.suggestedJiraSummary || request.prompt).slice(
            0,
            160,
          ),
          description:
            parsed.suggestedJiraDescription || parsed.recommendation,
          issuetype: { name: "Task" },
        },
      },
      citations: [baseCitation],
    });
  }

  const wantsSlack =
    request.evidence.some((item) => item.provider === "slack") ||
    /slack|notify|team|channel|message/.test(prompt);
  if (wantsSlack) {
    proposals.push({
      provider: "slack",
      operation: "message.post",
      rationale: "Notify the project channel after approval",
      payload: {
        text: `${request.project}: ${parsed.recommendation}`.slice(0, 300),
      },
      citations: [baseCitation],
    });
  }

  return proposals.filter((proposal) =>
    ALLOWED_PROPOSALS[proposal.provider]?.has(proposal.operation),
  );
}

function buildResponse(
  request: AgentContextRequestBody,
  parsed: PolicyRecommendation,
): AgentContextResponseBody {
  const evidenceKeys = request.evidence.map((item) => item.key);
  const baseCitation = evidenceKeys[0];

  // Citations must be a subset of the request evidence keys. Prefer the
  // model's cited references (intersected with real keys); otherwise cite
  // all collected evidence.
  const modelCited = parsed.evidence.filter((key) =>
    evidenceKeys.includes(key),
  );
  const citations =
    modelCited.length > 0
      ? Array.from(new Set(modelCited))
      : Array.from(new Set(evidenceKeys));

  const risk: RiskAssessment = {
    level: HIGH_SIGNAL.test(request.prompt) ? "high" : "medium",
    factors: [
      "Assessment grounded in the mission task and collected evidence",
    ],
    citations: [baseCitation],
  };

  const minutes = Math.min(240, Math.max(30, request.evidence.length * 15));
  const effort: EffortAssessment = {
    minutes,
    rationale: bounded(
      `Estimated from ${request.evidence.length} collected evidence item(s) and the mission scope.`,
      3,
      2000,
      "Estimated from collected evidence.",
    ),
    citations: [baseCitation],
  };

  const reviewer_candidates: ReviewerCandidate[] = [
    {
      identity: "project-maintainer",
      score: 0.6,
      reason: bounded(
        `Routed to the ${request.project} maintainer to review the proposed operational action.`,
        3,
        2000,
        "Configured project maintainer role.",
      ),
      citations: [baseCitation],
    },
  ];

  const confidence =
    typeof parsed.confidence === "number"
      ? Math.max(0, Math.min(1, parsed.confidence))
      : 0.6;

  return {
    contract_version: "1.0",
    context_summary: bounded(
      request.context_summary,
      3,
      5000,
      parsed.recommendation || "Mission context assembled.",
    ),
    risk,
    effort,
    reviewer_candidates,
    confidence,
    explanation: bounded(
      `${parsed.recommendation}\n\n${parsed.rationale}`,
      3,
      5000,
      "Reasoning grounded in collected evidence.",
    ),
    citations,
    proposals: buildProposals(request, parsed, baseCitation),
  };
}

/**
 * Runs the shared reasoning path over a backend AgentContextRequest and
 * returns a backend-valid AgentContextResponse. Throws when the request
 * carries no evidence (the response contract requires >= 1 citation).
 */
export async function analyzeMission(
  request: AgentContextRequestBody,
  gateway?: ModelGateway,
): Promise<AgentContextResponseBody> {
  if (!Array.isArray(request.evidence) || request.evidence.length === 0) {
    throw new Error(
      "AgentContextRequest requires at least one evidence item.",
    );
  }

  const blocks: EvidenceBlock[] = request.evidence.map((item) => ({
    source: item.provider,
    reference: item.key,
    title: item.title,
    content: item.url ? `${item.excerpt}\n(${item.url})` : item.excerpt,
  }));

  const parsed = await reasonOverMission({
    mission: request.prompt,
    context: request.knowledge_base ?? null,
    freshEvidence: renderEvidenceBlocks(blocks),
    gateway,
  });

  return buildResponse(request, parsed);
}
