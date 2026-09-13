import type { AgentStateType } from "../graph/state.js";

export async function critiqueActions(
  state: AgentStateType,
): Promise<Partial<AgentStateType>> {
  if (state.proposedActions.length === 0) {
    return {
      currentStep: "critique_actions",
      errors: ["Cannot critique without proposed actions."],
    };
  }

  const errors: string[] = [];

  const failedVerifications = state.verificationResults.filter(
    (result) => !result.verified,
  );

  if (failedVerifications.length > 0) {
    errors.push(
      `Verification failed for ${failedVerifications
        .map((result) => result.actionId)
        .join(", ")}.`,
    );
  }

  for (const action of state.proposedActions) {
    if (!action.target) {
      errors.push(`Action ${action.id} has no target.`);
    }

    if (!action.reason) {
      errors.push(`Action ${action.id} has no reason.`);
    }
  }

  return {
    currentStep: "critique_actions",
    errors,
  };
}