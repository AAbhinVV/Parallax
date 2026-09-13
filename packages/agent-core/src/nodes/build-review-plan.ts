import type { AgentStateType } from "../graph/state.js";
import type { ReviewerCandidate } from "../schemas/index.js";

function estimateReviewMinutes(
  state: AgentStateType,
): number {
  if (!state.pr || !state.risk) {
    return 30;
  }

  let minutes = 20;

  minutes += state.pr.filesChanged * 3;

  if (state.risk.level === "medium") {
    minutes += 15;
  }

  if (state.risk.level === "high") {
    minutes += 30;
  }

  if (state.risk.level === "critical") {
    minutes += 60;
  }

  return minutes;
}

function selectReviewer(
  state: AgentStateType,
): ReviewerCandidate | null {
  for (const candidate of state.reviewerCandidates) {
    const hasAvailability = state.availability.some(
      (slot) => slot.reviewerId === candidate.id,
    );

    if (hasAvailability) {
      return candidate;
    }
  }

  return null;
}

export async function buildReviewPlan(
  state: AgentStateType,
): Promise<Partial<AgentStateType>> {
  if (!state.risk) {
    return {
      currentStep: "build_review_plan",
      errors: ["Cannot build a review plan without risk assessment."],
    };
  }

  if (state.reviewerCandidates.length === 0) {
    return {
      currentStep: "build_review_plan",
      errors: ["Cannot build a review plan without reviewers."],
    };
  }

  const reviewer = selectReviewer(state);

  if (!reviewer) {
    return {
      currentStep: "build_review_plan",
      errors: ["No suitable reviewer is currently available."],
    };
  }

  const slot = state.availability.find(
    (item) => item.reviewerId === reviewer.id,
  );

  if (!slot) {
    return {
      currentStep: "build_review_plan",
      errors: ["Selected reviewer has no availability slot."],
    };
  }

  const estimatedMinutes = estimateReviewMinutes(state);

  const suggestedEndDate = new Date(
    new Date(slot.start).getTime() +
        estimatedMinutes * 60 * 1000,
  );

  const suggestedEnd =
    `${suggestedEndDate.toLocaleString("sv-SE", {
        timeZone: "Asia/Kolkata",
  }).replace(" ", "T")}+05:30`;

  const focusAreas = state.risk.signals.map(
    (signal) => signal.description,
  );

  return {
    currentStep: "build_review_plan",

    reviewPlan: {
      recommendedReviewerId: reviewer.id,
      recommendedReviewerName: reviewer.name,

      estimatedMinutes,

      suggestedStart: slot.start,
      suggestedEnd,

      focusAreas,

      reasoning:
        `Recommended ${reviewer.name} because they have the highest ` +
        `reviewer score among currently available candidates. ` +
        `The PR is classified as ${state.risk.level} risk ` +
        `(${state.risk.score}/100), so the review should prioritize ` +
        `the identified risk areas.`,
    },
  };
}