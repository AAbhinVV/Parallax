import { interrupt } from "@langchain/langgraph";

import type { AgentStateType } from "../graph/state.js";

export async function approvalGate(
  state: AgentStateType,
): Promise<Partial<AgentStateType>> {
  if (!state.policyDecision) {
    return {
      currentStep: "approval_gate",
      errors: ["Cannot enter approval gate without a policy decision."],
    };
  }

  if (!state.policyDecision.requiresApproval) {
    return {
      currentStep: "approval_gate",
      approvalStatus: "approved",
    };
  }

  const decision = interrupt({
    type: "approval_required",
    message: "Human approval is required before executing these actions.",
    actions: state.proposedActions,
    risk: state.risk,
  });

  if (decision === true || decision === "approved") {
    return {
      currentStep: "approval_gate",
      approvalStatus: "approved",
    };
  }

  return {
    currentStep: "approval_gate",
    approvalStatus: "rejected",
  };
}