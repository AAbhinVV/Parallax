import type { AgentStateType } from "../graph/state.js";
import { calculateRisk } from "../intelligence/risk.js";

export async function analyzeRisk(
  state: AgentStateType,
): Promise<Partial<AgentStateType>> {
  if (!state.pr) {
    return {
      currentStep: "analyze_risk",
      errors: ["Cannot analyze risk without a pull request."],
    };
  }

  const risk = calculateRisk(
    state.pr,
    state.evidence,
  );

  return {
    currentStep: "analyze_risk",
    risk,
  };
}