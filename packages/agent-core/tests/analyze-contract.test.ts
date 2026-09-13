import { afterEach, describe, expect, it } from "vitest";

import {
  analyzeMission,
  type AgentContextRequestBody,
} from "../src/reasoning/analyze.js";
import {
  overrideModelGateway,
  buildReasoningInput,
} from "../src/reasoning/reason.js";
import { overrideNotionTool } from "../src/nodes/analyze-notion-document.js";
import { analyzeNotionDocument } from "../src/nodes/analyze-notion-document.js";
import type { ModelGateway } from "../src/reasoning/model-gateway.js";
import type { MissionContext } from "../src/types/mission-context.js";
import type { AgentStateType } from "../src/graph/state.js";
import type { Evidence } from "../src/schemas/index.js";

function buildBackendRequest(
  overrides?: Partial<AgentContextRequestBody>,
): AgentContextRequestBody {
  return {
    contract_version: "1.0",
    mission_id: "6f1d2c8e-0000-4000-8000-00000000000a",
    prompt:
      "Create the Jira task from the policy brief and notify the team.",
    project: "Policy",
    context_summary: "One Notion policy brief was collected.",
    evidence: [
      {
        key: "notion:page:037c",
        provider: "notion",
        external_id: "037c",
        title: "Policy Brief",
        excerpt: "The policy brief recommends an AIA process.",
        url: "https://notion.so/037c",
      },
      {
        key: "jira:issue:KAN-5",
        provider: "jira",
        external_id: "KAN-5",
        title: "KAN-5",
        excerpt: "KAN-5 exists with status Done.",
      },
    ],
    knowledge_base: null,
    ...overrides,
  };
}

const knowledgeBase: MissionContext = {
  task: "Create the Jira task from the policy brief and notify the team.",
  mission_status: "running",
  result_summary: null,
  facts: [
    {
      id: "f-1",
      kind: "source_fact",
      source: "jira",
      source_ref: "KAN-5",
      fact: "KAN-5: Issue status is Done",
      data: {},
      observed_at: "2026-09-13T19:42:10+00:00",
      verified_at: "2026-09-13T19:43:00+00:00",
      status: "verified",
      confidence: null,
    },
  ],
  decisions: [],
  recent_actions: [],
  pending_actions: [],
  verified_outcomes: [],
  conflicts: [],
};

function fakeGateway(response: string): ModelGateway {
  return {
    async invoke() {
      return response;
    },
  };
}

const ACTION_RESPONSE = `{
  "status": "action_required",
  "recommendation": "Create the Jira task for the AIA policy action",
  "rationale": "The task asks for a Jira task and the policy brief supports it",
  "confidence": 0.9,
  "uncertainties": [],
  "evidence": ["notion:page:037c", "invented:key"],
  "suggestedJiraSummary": "Implement AIA process",
  "suggestedJiraDescription": "Create the Jira task for the documented AIA implementation"
}`;

afterEach(() => {
  overrideModelGateway(null);
  overrideNotionTool(null);
});

describe("analyzeMission", () => {
  it("returns a backend-valid AgentContextResponse", async () => {
    overrideModelGateway(fakeGateway(ACTION_RESPONSE));

    const response = await analyzeMission(buildBackendRequest());

    expect(response.contract_version).toBe("1.0");
    expect(response.context_summary.length).toBeGreaterThanOrEqual(3);
    expect(["low", "medium", "high", "critical"]).toContain(
      response.risk.level,
    );
    expect(response.risk.factors.length).toBeGreaterThanOrEqual(1);
    expect(response.effort.minutes).toBeGreaterThanOrEqual(5);
    expect(response.effort.minutes).toBeLessThanOrEqual(2400);
    expect(response.reviewer_candidates.length).toBeGreaterThanOrEqual(1);
    expect(response.confidence).toBeGreaterThanOrEqual(0);
    expect(response.confidence).toBeLessThanOrEqual(1);
    expect(response.explanation.length).toBeGreaterThanOrEqual(3);
    expect(response.citations.length).toBeGreaterThanOrEqual(1);
  });

  it("cites only evidence keys the backend actually sent", async () => {
    overrideModelGateway(fakeGateway(ACTION_RESPONSE));

    const response = await analyzeMission(buildBackendRequest());
    const evidenceKeys = new Set(
      buildBackendRequest().evidence.map((item) => item.key),
    );

    const allCitations = [
      ...response.citations,
      ...response.risk.citations,
      ...response.effort.citations,
      ...response.reviewer_candidates.flatMap((r) => r.citations),
      ...response.proposals.flatMap((p) => p.citations),
    ];

    expect(allCitations.length).toBeGreaterThan(0);
    for (const citation of allCitations) {
      expect(evidenceKeys.has(citation)).toBe(true);
    }
    expect(response.citations).toContain("notion:page:037c");
    expect(response.citations).not.toContain("invented:key");
  });

  it("proposes only operations the backend allows per provider", async () => {
    overrideModelGateway(fakeGateway(ACTION_RESPONSE));

    const response = await analyzeMission(buildBackendRequest());

    expect(response.proposals.length).toBeGreaterThan(0);
    for (const proposal of response.proposals) {
      const allowed: Record<string, string[]> = {
        github: [],
        jira: ["issue.create", "issue.update"],
        notion: ["page.append"],
        slack: ["message.post", "message.update"],
      };
      expect(allowed[proposal.provider]).toContain(proposal.operation);
      expect(proposal.rationale.length).toBeGreaterThanOrEqual(3);
    }
  });

  it("proposes no actions when reasoning says already completed", async () => {
    overrideModelGateway(
      fakeGateway(`{
        "status": "already_completed",
        "recommendation": "Objective already satisfied",
        "rationale": "KAN-5 exists and is verified Done",
        "confidence": 0.97,
        "uncertainties": [],
        "evidence": ["jira:issue:KAN-5"],
        "suggestedJiraSummary": "",
        "suggestedJiraDescription": ""
      }`),
    );

    const response = await analyzeMission(
      buildBackendRequest({ knowledge_base: knowledgeBase }),
    );

    expect(response.proposals).toEqual([]);
    expect(response.confidence).toBe(0.97);
  });

  it("passes the knowledge base and evidence to the reasoning path", async () => {
    let receivedPrompt = "";

    overrideModelGateway({
      async invoke(messages) {
        receivedPrompt = messages
          .map((message) => String(message.content))
          .join("\n");

        return ACTION_RESPONSE;
      },
    });

    await analyzeMission(
      buildBackendRequest({ knowledge_base: knowledgeBase }),
    );

    expect(receivedPrompt).toContain("CURRENT TASK");
    expect(receivedPrompt).toContain("OPERATIONAL KNOWLEDGE BASE");
    expect(receivedPrompt).toContain("FRESH SOURCE EVIDENCE");
    expect(receivedPrompt).toContain("KAN-5: Issue status is Done");
    expect(receivedPrompt).toContain("[SOURCE: notion]");
    expect(receivedPrompt).toContain("Reference: notion:page:037c");
  });

  it("rejects requests without evidence (contract needs >= 1 citation)", async () => {
    overrideModelGateway(fakeGateway(ACTION_RESPONSE));

    await expect(
      analyzeMission(buildBackendRequest({ evidence: [] })),
    ).rejects.toThrow(/at least one evidence item/i);
  });

  it("shares the same reasoning input builder as the graph node path", async () => {
    const canonical = buildReasoningInput(
      "Create the Jira task.",
      knowledgeBase,
      "No fresh source evidence available.",
    );

    expect(canonical).toContain("CURRENT TASK");
    expect(canonical).toContain("OPERATIONAL KNOWLEDGE BASE");
    expect(canonical).toContain("FRESH SOURCE EVIDENCE");

    // The /v1/analyze path and the node path both consume this builder via
    // reasonOverMission; prove the node still funnels through it.
    let nodePrompt = "";
    overrideModelGateway({
      async invoke(messages) {
        nodePrompt = messages.map((m) => String(m.content)).join("\n");

        return ACTION_RESPONSE;
      },
    });
    overrideNotionTool({
      async getPageContent(): Promise<Evidence> {
        return {
          source: "notion",
          type: "page",
          title: "Policy Brief",
          content: "The policy brief recommends an AIA process.",
          url: "https://notion.so/037c",
        };
      },
      extractPageId: () => "037c217a037c217a037c217a037c217a",
    });

    const state: AgentStateType = {
      mission: "Create the Jira task.",
      pr: null,
      evidence: [],
      gaps: [],
      risk: null,
      reviewEffort: null,
      reviewerCandidates: [],
      availability: [],
      reviewPlan: null,
      contextPack: null,
      policyRecommendation: null,
      proposedActions: [],
      policyDecision: null,
      executionResults: [],
      verificationResults: [],
      slackSummary: "",
      auditEvents: [],
      context: knowledgeBase,
      approvalStatus: "not_required",
      currentStep: "start",
      errors: [],
    };

    await analyzeNotionDocument(state);

    expect(nodePrompt).toContain("CURRENT TASK");
    expect(nodePrompt).toContain("KAN-5: Issue status is Done");
    expect(nodePrompt).toContain("OPERATIONAL KNOWLEDGE BASE");
    expect(nodePrompt).toContain("FRESH SOURCE EVIDENCE");
  });
});
