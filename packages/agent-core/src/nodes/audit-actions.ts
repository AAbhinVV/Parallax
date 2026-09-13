import type { AgentStateType } from "../graph/state.js";
import type { AuditEvent } from "../schemas/index.js";

export async function auditActions(
  state: AgentStateType,
): Promise<Partial<AgentStateType>> {
  if (state.executionResults.length === 0) {
    return {
      currentStep: "audit_actions",
      errors: ["Cannot create audit events because no actions were executed."],
    };
  }

  const executionByActionId = new Map(
    state.executionResults.map((result) => [result.actionId, result]),
  );

  const auditEvents: AuditEvent[] = state.proposedActions.map((action) => {
    const execution = executionByActionId.get(action.id);

    return {
      actionId: action.id,
      action: action.type,
      reason: action.reason,
      timestamp: new Date().toISOString(),
      success: execution?.success ?? false,
    };
  });

  return {
    currentStep: "audit_actions",
    auditEvents,
  };
}