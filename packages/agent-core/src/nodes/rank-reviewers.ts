import type { AgentStateType } from "../graph/state.js";
import { rankReviewerCandidates } from "../intelligence/reviewer-ranking.js";
import { MockReviewerTool } from "../tools/mock-reviewers.js";

const reviewerTool = new MockReviewerTool();

export async function rankReviewers(
  state: AgentStateType,
): Promise<Partial<AgentStateType>> {
  if (!state.pr) {
    return {
      currentStep: "rank_reviewers",
      errors: ["Cannot rank reviewers without a pull request."],
    };
  }

  const candidates = await reviewerTool.getCandidates(state.pr);

  const rankedCandidates = rankReviewerCandidates(candidates);

  return {
    currentStep: "rank_reviewers",
    reviewerCandidates: rankedCandidates,
  };
}