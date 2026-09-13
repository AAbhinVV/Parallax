import type { AgentStateType } from "../graph/state.js";
import type { Evidence } from "../schemas/index.js";
import {
  NotionRestTool,
  extractNotionPageId,
} from "../tools/notion.js";
import type { NotionTool } from "../tools/notion.js";
import { reasonOverMission } from "../reasoning/reason.js";
import type { PolicyRecommendation } from "../schemas/policy-recommendation.js";

/*
 * Reasoning itself lives in ../reasoning/reason.ts (the one agent path).
 * This node owns Notion-specific evidence gathering and then calls the
 * shared reasoning core. buildReasoningInput / overrideModelGateway are
 * re-exported so existing imports and tests keep working.
 */
export {
  buildReasoningInput,
  overrideModelGateway,
} from "../reasoning/reason.js";

/*
 * The Notion tool is instantiated lazily so importing this module (e.g. in
 * tests) does not require credentials. The override is a test-only seam;
 * production always falls through to the real tool.
 */
let notion: NotionRestTool | null = null;
let notionOverride: NotionTool | null = null;

function getNotionTool(): NotionTool {
  if (notionOverride) {
    return notionOverride;
  }

  notion ??= new NotionRestTool();

  return notion;
}

/** Test-only seam: replace the Notion tool (pass null to restore). */
export function overrideNotionTool(tool: NotionTool | null): void {
  notionOverride = tool;
}

/**
 * Renders freshly retrieved evidence as a provenance block so the model can
 * connect an eventual decision back to a source reference.
 */
export function renderFreshEvidence(
  evidence: Evidence | null,
): string {
  if (!evidence) {
    return "No fresh source evidence available.";
  }

  return [
    `[SOURCE: ${evidence.source}]`,
    `Reference: ${evidence.url ?? evidence.type}`,
    `Title: ${evidence.title}`,
    "Content:",
    evidence.content,
  ].join("\n");
}

export async function analyzeNotionDocument(
  state: AgentStateType,
): Promise<Partial<AgentStateType>> {
  try {
    const pageId = extractNotionPageId(state.mission);

    let freshEvidence: Evidence | null = null;
    if (pageId) {
      freshEvidence = await getNotionTool().getPageContent(pageId);
    }

    const parsed: PolicyRecommendation = await reasonOverMission({
      mission: state.mission,
      context: state.context ?? null,
      freshEvidence: renderFreshEvidence(freshEvidence),
    });

    return {
      currentStep: "analyze_notion_document",
      evidence: freshEvidence ? [freshEvidence] : [],
      policyRecommendation: parsed,
      slackSummary:
        `Recommended action: ${parsed.recommendation}\n\n` +
        `Rationale: ${parsed.rationale}`,
    };
  } catch (error) {
    return {
      currentStep: "analyze_notion_document",
      errors: [
        `Failed to analyze mission context: ${
          error instanceof Error
            ? error.message
            : String(error)
        }`,
      ],
    };
  }
}
