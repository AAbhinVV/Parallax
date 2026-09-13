import type { AgentStateType } from "./graph/state.js";
import type { DemoResult } from "./schemas/demo-result.js";

export function buildDemoResult(state: AgentStateType): DemoResult {
  const topReviewer = state.reviewerCandidates[0];

  if (!state.risk) {
    throw new Error("Cannot build demo result without risk assessment.");
  }

  if (!state.reviewPlan) {
    throw new Error("Cannot build demo result without review plan.");
  }

  if (!state.policyDecision) {
    throw new Error("Cannot build demo result without policy decision.");
  }

  if (!topReviewer) {
    throw new Error("Cannot build demo result without a reviewer.");
  }

  return {
    mission: state.mission,

    pr: state.pr,

    gaps: state.gaps,

    currentStep: state.currentStep,

    risk: {
      level: state.risk.level,
      score: state.risk.score,
      confidence: state.risk.confidence,
      explanation: state.risk.explanation,
    },

    reviewer: {
      id: topReviewer.id,
      name: topReviewer.name,
      score: topReviewer.totalScore,
      reasons: topReviewer.reasons,
    },

    review: {
      estimatedMinutes: state.reviewPlan.estimatedMinutes,
      suggestedStart: state.reviewPlan.suggestedStart,
      suggestedEnd: state.reviewPlan.suggestedEnd,
      focusAreas: state.reviewPlan.focusAreas,
      reasoning: state.reviewPlan.reasoning,
    },

    contextPack: state.contextPack,

    actions: state.proposedActions,

    policy: {
      allowed: state.policyDecision.allowed,
      requiresApproval: state.policyDecision.requiresApproval,
      reason: state.policyDecision.reason,
    },

    execution: state.executionResults,

    verification: state.verificationResults,

    slackSummary: state.slackSummary,

    audit: state.auditEvents,

    approvalStatus: state.approvalStatus,
  };
}