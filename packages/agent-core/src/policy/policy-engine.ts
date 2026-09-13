import type {
  ActionProposal,
  RiskAssessment,
  PolicyDecision,
} from "../schemas/index.js";

export function evaluateActionPolicy(
  action: ActionProposal,
  risk: RiskAssessment,
): PolicyDecision {
  if (risk.level === "critical") {
    return {
      allowed: true,
      requiresApproval: true,
      reason:
        "Critical-risk changes require explicit human approval before execution.",
    };
  }

  if (risk.level === "high") {
    return {
      allowed: true,
      requiresApproval: true,
      reason:
        "High-risk changes require explicit human approval before execution.",
    };
  }

  if (
    action.type === "jira.create_issue" ||
    action.type === "jira.update_issue" ||
    action.type === "github.update_pull_request" ||
    action.type === "notion.update_documentation"
  ) {
    return {
      allowed: true,
      requiresApproval: false,
      reason:
        "The proposed cross-tool action is permitted for this risk level.",
    };
  }

  return {
    allowed: false,
    requiresApproval: false,
    reason:
      "The requested action is not permitted by policy.",
  };
}