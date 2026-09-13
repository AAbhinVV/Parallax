/**
 * Normalized mission contract shared by Agent Core's HTTP API,
 * the FastAPI backend, and (indirectly) the frontend.
 */

export type MissionStatus =
  | "planning"
  | "waiting_for_approval"
  | "running"
  | "completed"
  | "partially_complete"
  | "failed"
  | "rejected";

export interface MissionResponse {
  missionId: string;
  status: MissionStatus;
  currentStep: string;
  progress: number;
  approvalStatus: string;
  policyRecommendation: unknown;
  proposedActions: unknown[];
  executionResults: unknown[];
  verificationResults: unknown[];
  slackSummary: string;
  errors: string[];
}

/**
 * Ordered stages of the primary (Notion) mission pipeline.
 * The index of the current step drives the progress percentage.
 */
export const MISSION_STEPS = [
  "analyze_notion_document",
  "propose_actions",
  "evaluate_policy",
  "approval_gate",
  "cross_tool_updates",
  "verify_actions",
  "slack_summary",
  "finalize_notion",
  "audit_actions",
] as const;

export function getProgress(step: string): number {
  const index = MISSION_STEPS.indexOf(
    step as (typeof MISSION_STEPS)[number],
  );

  if (index === -1) {
    return 0;
  }

  return Math.round(
    ((index + 1) / MISSION_STEPS.length) * 100,
  );
}
