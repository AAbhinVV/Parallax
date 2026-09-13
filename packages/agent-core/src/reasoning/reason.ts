import { HumanMessage, SystemMessage } from "@langchain/core/messages";

import { GeminiGateway } from "./gemini-gateway.js";
import type { ModelGateway } from "./model-gateway.js";
import {
  PARALLAX_SYSTEM_PROMPT,
  renderKnowledgeBase,
} from "./system-prompt.js";
import type { MissionContext } from "../types/mission-context.js";
import {
  PolicyRecommendationSchema,
  type PolicyRecommendation,
} from "../schemas/policy-recommendation.js";

/*
 * The one reasoning path. Every interface (LangGraph node, /v1/analyze,
 * /missions) funnels through reasonOverMission, so there is a single agent
 * behaviour rather than one implementation per transport.
 *
 * The Gemini gateway is instantiated lazily so importing this module (e.g.
 * in tests) does not require credentials. The override is a test-only seam.
 */
let model: GeminiGateway | null = null;
let gatewayOverride: ModelGateway | null = null;

export function getModelGateway(): ModelGateway {
  if (gatewayOverride) {
    return gatewayOverride;
  }

  model ??= new GeminiGateway();

  return model;
}

/** Test-only seam: replace the model gateway (pass null to restore). */
export function overrideModelGateway(gateway: ModelGateway | null): void {
  gatewayOverride = gateway;
}

/**
 * A freshly retrieved piece of source information with provenance so the
 * model can connect an eventual decision back to a source reference.
 */
export type EvidenceBlock = {
  source: string;
  reference: string;
  title: string;
  content: string;
};

export function renderEvidenceBlocks(blocks: EvidenceBlock[]): string {
  if (blocks.length === 0) {
    return "No fresh source evidence available.";
  }

  return blocks
    .map((block) =>
      [
        `[SOURCE: ${block.source}]`,
        `Reference: ${block.reference}`,
        `Title: ${block.title}`,
        "Content:",
        block.content,
      ].join("\n"),
    )
    .join("\n\n");
}

/**
 * Canonical reasoning input: current task, then operational memory, then
 * fresh evidence — in that order, kept as separate blocks so memory can
 * never masquerade as fresh source truth.
 */
export function buildReasoningInput(
  mission: string,
  context: MissionContext | null,
  freshEvidence: string,
): string {
  return [
    "CURRENT TASK",
    "",
    mission,
    "",
    "OPERATIONAL KNOWLEDGE BASE",
    "",
    renderKnowledgeBase(context),
    "",
    "FRESH SOURCE EVIDENCE",
    "",
    freshEvidence || "No fresh source evidence available.",
  ].join("\n");
}

export const JSON_RESPONSE_INSTRUCTION = `Determine the single best operational action for the current task.

Respond with ONLY valid JSON matching this structure:
{
  "status": "action_required | already_completed | needs_clarification | no_action_required",
  "recommendation": "single best next operational action, or a short statement when no action is required",
  "rationale": "why this action is supported by the task, knowledge base, and fresh evidence above",
  "confidence": 0.94,
  "uncertainties": ["missing or conflicting information that affects the decision"],
  "evidence": ["source references cited above, e.g. notion:037c... or jira:KAN-5"],
  "suggestedJiraSummary": "concise Jira task title",
  "suggestedJiraDescription": "detailed Jira task description"
}

Ground every statement in the task, the knowledge base, or the fresh
evidence above. If information is missing or conflicting, report it in
uncertainties and lower confidence instead of inventing details. Use
status "already_completed" only when verified knowledge and verified
outcomes show the operational objective is already satisfied, and
"needs_clarification" when the task cannot be acted on without more
information.`;

/**
 * Runs the single Parallax reasoning step: task + operational memory +
 * fresh evidence -> a structured, schema-validated decision. Callers own
 * evidence gathering (Notion retrieval, backend-collected evidence, ...)
 * and response translation; the reasoning itself lives only here.
 */
export async function reasonOverMission(params: {
  mission: string;
  context: MissionContext | null;
  freshEvidence: string;
  gateway?: ModelGateway;
}): Promise<PolicyRecommendation> {
  const gateway = params.gateway ?? getModelGateway();

  const response = await gateway.invoke([
    new SystemMessage(PARALLAX_SYSTEM_PROMPT),
    new HumanMessage(
      `${buildReasoningInput(
        params.mission,
        params.context,
        params.freshEvidence,
      )}\n\n${JSON_RESPONSE_INSTRUCTION}`,
    ),
  ]);

  const jsonStart = response.indexOf("{");
  const jsonEnd = response.lastIndexOf("}");

  if (jsonStart === -1 || jsonEnd === -1 || jsonEnd <= jsonStart) {
    throw new Error("Gemini did not return a JSON object.");
  }

  return PolicyRecommendationSchema.parse(
    JSON.parse(response.slice(jsonStart, jsonEnd + 1)),
  );
}
