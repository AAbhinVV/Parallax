import { afterEach, describe, expect, it } from "vitest";
import type { BaseMessage } from "@langchain/core/messages";

import {
  analyzeNotionDocument,
  buildReasoningInput,
  overrideModelGateway,
  overrideNotionTool,
  renderFreshEvidence,
} from "../src/nodes/analyze-notion-document.js";
import { PARALLAX_SYSTEM_PROMPT } from "../src/reasoning/system-prompt.js";
import type { ModelGateway } from "../src/reasoning/model-gateway.js";
import type { NotionTool } from "../src/tools/notion.js";
import type { AgentStateType } from "../src/graph/state.js";
import type { Evidence } from "../src/schemas/index.js";
import type { MissionContext } from "../src/types/mission-context.js";

function buildState(overrides?: Partial<AgentStateType>): AgentStateType {
  return {
    mission: "Create the Jira task for the policy brief and notify the team.",
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
    context: null,
    approvalStatus: "not_required",
    currentStep: "start",
    errors: [],
    ...overrides,
  };
}

const memoryContext: MissionContext = {
  task: "Create the Jira task for the policy brief and notify the team.",
  mission_status: "running",
  result_summary: null,
  facts: [
    {
      id: "f-1",
      kind: "source_fact",
      source: "jira",
      source_ref: "KAN-5",
      fact: "KAN-5: Issue already exists",
      data: {},
      observed_at: "2026-09-13T10:00:00Z",
      verified_at: "2026-09-13T10:01:00Z",
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

const freshNotionEvidence: Evidence = {
  source: "notion",
  type: "page",
  title: "Policy Brief",
  content: "The policy brief recommends an AIA process.",
  url: "https://notion.so/037c217a037c217a037c217a037c217a",
};

const NOTION_URL = "https://notion.so/037c217a037c217a037c217a037c217a";

function recordingGateway(response: string): {
  gateway: ModelGateway;
  messages: () => BaseMessage[];
} {
  const recorded: BaseMessage[] = [];

  return {
    gateway: {
      async invoke(messages) {
        recorded.push(...messages);

        return response;
      },
    },
    messages: () => recorded,
  };
}

function fakeNotionTool(evidence: Evidence): NotionTool {
  return {
    async getPageContent() {
      return evidence;
    },
    extractPageId(text: string) {
      return text.includes(evidence.url ?? "") ? evidence.url ?? null : null;
    },
  };
}

const ACTION_RESPONSE = `{
  "status": "action_required",
  "recommendation": "Create the Jira task for the AIA policy action",
  "rationale": "The task asks for a Jira task and the policy brief supports it",
  "confidence": 0.9,
  "uncertainties": [],
  "evidence": ["notion:037c217a"],
  "suggestedJiraSummary": "Implement AIA process",
  "suggestedJiraDescription": "Create the Jira task for the documented AIA implementation"
}`;

afterEach(() => {
  overrideModelGateway(null);
  overrideNotionTool(null);
});

describe("buildReasoningInput", () => {
  it("orders task, then knowledge base, then fresh evidence", () => {
    const input = buildReasoningInput(
      "Create the Jira task.",
      memoryContext,
      "[SOURCE: jira]\nReference: jira:KAN-5\nStatus = Done.",
    );

    const taskIndex = input.indexOf("CURRENT TASK");
    const knowledgeIndex = input.indexOf("OPERATIONAL KNOWLEDGE BASE");
    const freshIndex = input.indexOf("FRESH SOURCE EVIDENCE");

    expect(taskIndex).toBeGreaterThanOrEqual(0);
    expect(knowledgeIndex).toBeGreaterThan(taskIndex);
    expect(freshIndex).toBeGreaterThan(knowledgeIndex);
  });

  it("contains the mission, memory facts and fresh evidence", () => {
    const input = buildReasoningInput(
      "Create the Jira task.",
      memoryContext,
      "[SOURCE: jira]\nReference: jira:KAN-5\nStatus = Done.",
    );

    expect(input).toContain("Create the Jira task.");
    expect(input).toContain("KAN-5: Issue already exists");
    expect(input).toContain("Status = Done.");
  });

  it("keeps empty blocks explicit instead of dropping them", () => {
    const input = buildReasoningInput("Task only.", null, "");

    expect(input).toContain("No operational knowledge base is available.");
    expect(input).toContain("No fresh source evidence available.");
  });
});

describe("renderFreshEvidence", () => {
  it("renders fresh evidence with provenance", () => {
    const output = renderFreshEvidence(freshNotionEvidence);

    expect(output).toContain("[SOURCE: notion]");
    expect(output).toContain(
      `Reference: ${NOTION_URL}`,
    );
    expect(output).toContain("Title: Policy Brief");
    expect(output).toContain("The policy brief recommends an AIA process.");
  });

  it("keeps a missing-evidence placeholder explicit", () => {
    expect(renderFreshEvidence(null)).toBe(
      "No fresh source evidence available.",
    );
  });
});

describe("analyzeNotionDocument", () => {
  it("passes the canonical system prompt and full reasoning input to the model", async () => {
    const { gateway, messages } = recordingGateway(ACTION_RESPONSE);
    overrideModelGateway(gateway);

    const result = await analyzeNotionDocument(
      buildState({ context: memoryContext }),
    );

    expect(result.errors).toBeUndefined();

    const recorded = messages();
    expect(recorded).toHaveLength(2);
    expect(recorded[0].content).toBe(PARALLAX_SYSTEM_PROMPT);

    const human = recorded[1].content as string;
    expect(human).toContain("CURRENT TASK");
    expect(human).toContain("OPERATIONAL KNOWLEDGE BASE");
    expect(human).toContain("FRESH SOURCE EVIDENCE");
    expect(human).toContain("KAN-5: Issue already exists");
    expect(human).toContain("No fresh source evidence available.");
  });

  it("reasons over task and memory without requiring a Notion document", async () => {
    const { gateway } = recordingGateway(ACTION_RESPONSE);
    overrideModelGateway(gateway);

    const result = await analyzeNotionDocument(
      buildState({ context: memoryContext }),
    );

    expect(result.errors).toBeUndefined();
    expect(result.policyRecommendation).toBeDefined();
    expect(result.evidence).toEqual([]);
    expect(result.policyRecommendation?.status).toBe("action_required");
  });

  it("does not reason over Notion content that was never retrieved", async () => {
    const { gateway, messages } = recordingGateway(ACTION_RESPONSE);
    overrideModelGateway(gateway);

    await analyzeNotionDocument(buildState({ context: memoryContext }));

    const human = messages()[1].content as string;
    expect(human).not.toContain("Policy Brief");
  });

  it("preserves low-confidence structured uncertainty without repair", async () => {
    const { gateway } = recordingGateway(`{
      "status": "needs_clarification",
      "recommendation": "Unable to determine the target Jira project",
      "rationale": "The task does not identify which Jira project should be updated",
      "confidence": 0.31,
      "uncertainties": ["No Jira project is identified."],
      "evidence": [],
      "suggestedJiraSummary": "",
      "suggestedJiraDescription": ""
    }`);
    overrideModelGateway(gateway);

    const result = await analyzeNotionDocument(
      buildState({ context: memoryContext }),
    );

    expect(result.errors).toBeUndefined();
    expect(result.policyRecommendation?.status).toBe("needs_clarification");
    expect(result.policyRecommendation?.confidence).toBe(0.31);
    expect(result.policyRecommendation?.uncertainties).toEqual([
      "No Jira project is identified.",
    ]);
  });

  it("returns unsupported model output unchanged for backend validation to reject", async () => {
    const { gateway } = recordingGateway(`{
      "status": "action_required",
      "recommendation": "Update Jira KAN-999",
      "rationale": "Invented issue",
      "confidence": 0.5,
      "uncertainties": [],
      "evidence": [],
      "suggestedJiraSummary": "KAN-999",
      "suggestedJiraDescription": "Update KAN-999"
    }`);
    overrideModelGateway(gateway);

    const result = await analyzeNotionDocument(
      buildState({ context: memoryContext }),
    );

    expect(result.errors).toBeUndefined();
    expect(result.policyRecommendation?.recommendation).toBe(
      "Update Jira KAN-999",
    );
    expect(result.evidence).toEqual([]);
  });

  it("includes retrieved Notion evidence as fresh source content", async () => {
    const { gateway, messages } = recordingGateway(ACTION_RESPONSE);
    overrideModelGateway(gateway);
    overrideNotionTool(fakeNotionTool(freshNotionEvidence));

    const result = await analyzeNotionDocument(
      buildState({
        mission: `Read ${NOTION_URL} and create the Jira task.`,
        context: memoryContext,
      }),
    );

    expect(result.errors).toBeUndefined();

    const human = messages()[1].content as string;
    expect(human).toContain("[SOURCE: notion]");
    expect(human).toContain("Title: Policy Brief");

    const fetched = result.evidence as Evidence[] | undefined;
    expect(fetched).toHaveLength(1);
    expect(fetched?.[0].source).toBe("notion");
  });
});
