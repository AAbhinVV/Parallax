import type {
  ReviewerCandidate,
} from "../schemas/index.js";

interface ReviewerScoreInput {
  ownershipScore: number;
  skillMatchScore: number;
  historicalScore: number;
  availabilityScore: number;
  loadScore: number;
  recencyScore: number;
}

function calculateTotalScore(
  scores: ReviewerScoreInput,
): number {
  const weightedScore =
    scores.ownershipScore * 0.25 +
    scores.skillMatchScore * 0.25 +
    scores.historicalScore * 0.15 +
    scores.availabilityScore * 0.15 +
    scores.loadScore * 0.10 +
    scores.recencyScore * 0.10;

  return Math.round(weightedScore);
}

export function rankReviewerCandidates(
  candidates: ReviewerCandidate[],
): ReviewerCandidate[] {
  return candidates
    .map((candidate) => ({
      ...candidate,
      totalScore: calculateTotalScore(candidate),
    }))
    .sort((a, b) => b.totalScore - a.totalScore);
}