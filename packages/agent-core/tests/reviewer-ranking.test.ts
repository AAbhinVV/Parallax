import { describe, expect, it } from "vitest";

import { rankReviewerCandidates } from "../src/intelligence/reviewer-ranking.js";
import type { ReviewerCandidate } from "../src/schemas/index.js";

describe("rankReviewerCandidates", () => {
  it("ranks the strongest reviewer first", () => {
    const candidates: ReviewerCandidate[] = [
      {
        id: "reviewer-1",
        name: "Priya Sharma",
        ownershipScore: 95,
        skillMatchScore: 92,
        historicalScore: 88,
        availabilityScore: 80,
        loadScore: 75,
        recencyScore: 90,
        totalScore: 0,
        reasons: ["Strong payment ownership"],
      },
      {
        id: "reviewer-2",
        name: "Rahul Verma",
        ownershipScore: 82,
        skillMatchScore: 90,
        historicalScore: 85,
        availabilityScore: 95,
        loadScore: 90,
        recencyScore: 70,
        totalScore: 0,
        reasons: ["Strong backend expertise"],
      },
      {
        id: "reviewer-3",
        name: "Ananya Singh",
        ownershipScore: 65,
        skillMatchScore: 78,
        historicalScore: 82,
        availabilityScore: 70,
        loadScore: 60,
        recencyScore: 85,
        totalScore: 0,
        reasons: ["Good backend expertise"],
      },
    ];

    const ranked = rankReviewerCandidates(candidates);

    expect(ranked[0].id).toBe("reviewer-1");
    expect(ranked[0].name).toBe("Priya Sharma");
    expect(ranked[0].totalScore).toBe(88);

    expect(ranked[1].id).toBe("reviewer-2");
    expect(ranked[2].id).toBe("reviewer-3");
  });
});