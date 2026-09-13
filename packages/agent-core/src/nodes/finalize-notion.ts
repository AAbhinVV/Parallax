import type { AgentStateType } from "../graph/state.js";

export async function finalizeNotionDocumentation(
  state: AgentStateType,
): Promise<Partial<AgentStateType>> {
  if (!state.slackSummary) {
    return {
      currentStep: "finalize_notion",
      errors: [
        "Cannot finalize Notion documentation before the verified Slack summary.",
      ],
    };
  }

  if (
    state.verificationResults.length === 0 ||
    !state.verificationResults.every((result) => result.verified)
  ) {
    return {
      currentStep: "finalize_notion",
      errors: [
        "Cannot finalize Notion documentation because actions are not fully verified.",
      ],
    };
  }

  return {
    currentStep: "finalize_notion",
  };
}
