import type { AgentStateType } from "../graph/state.js";
import { evaluateActionPolicy } from "../policy/policy-engine.js";

export async function evaluatePolicy(
  state: AgentStateType,
): Promise<Partial<AgentStateType>> {
  if (state.proposedActions.length === 0) {
    return {
      currentStep: "evaluate_policy",
      errors: [
        "Cannot evaluate policy without proposed actions.",
      ],
    };
  }

  /*
   * Notion policy mission.
   *
   * There is no PR risk assessment in this path.
   * The recommendation itself is the basis for the proposed action,
   * and human approval is mandatory before creating the Jira task.
   */
  if (state.policyRecommendation) {
    return {
      currentStep: "evaluate_policy",
      policyDecision: {
        allowed: true,
        requiresApproval: true,
        reason:
          "A Jira task derived from a policy recommendation requires explicit human approval before execution.",
      },
      approvalStatus: "pending",
    };
  }

  /*
   * Existing PR workflow.
   */
  if (!state.risk) {
    return {
      currentStep: "evaluate_policy",
      errors: [
        "Cannot evaluate policy without a risk assessment.",
      ],
    };
  }

  const actionsWithPolicy = state.proposedActions.map(
    (action) => {
      const decision = evaluateActionPolicy(
        action,
        state.risk!,
      );

      return {
        ...action,
        requiresApproval: decision.requiresApproval,
      };
    },
  );

  const decisions = state.proposedActions.map(
    (action) =>
      evaluateActionPolicy(
        action,
        state.risk!,
      ),
  );

  const allAllowed = decisions.every(
    (decision) => decision.allowed,
  );

  const requiresApproval = decisions.some(
    (decision) => decision.requiresApproval,
  );

  const reason = decisions
    .map((decision) => decision.reason)
    .join(" ");

  return {
    currentStep: "evaluate_policy",
    proposedActions: actionsWithPolicy,
    policyDecision: {
      allowed: allAllowed,
      requiresApproval,
      reason,
    },
    approvalStatus: requiresApproval
      ? "pending"
      : "not_required",
  };
}