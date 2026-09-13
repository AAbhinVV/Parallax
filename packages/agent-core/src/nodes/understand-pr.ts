import type { AgentStateType } from "../graph/state.js";

export async function understandPR(
  state: AgentStateType,
): Promise<Partial<AgentStateType>> {
  if (!state.pr) {
    return {
      currentStep: "understand_pr",
      errors: ["No pull request was provided."],
    };
  }

  return {
    currentStep: "understand_pr",
    evidence: [
      {
        source: "github",
        type: "pull_request",
        title: state.pr.title,
        content: state.pr.description,
        url: state.pr.url,
      },
    ],
  };
}