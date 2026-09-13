import type { PR, ReviewerCandidate } from "../schemas/index.js";

export interface ReviewerTool {
  getCandidates(pr: PR): Promise<ReviewerCandidate[]>;
}

export class MockReviewerTool implements ReviewerTool {
  async getCandidates(_pr: PR): Promise<ReviewerCandidate[]> {
    return [
      {
        id: "reviewer-1",
        name: "Priya Sharma",
        ownershipScore: 95,
        skillMatchScore: 92,
        historicalScore: 88,
        availabilityScore: 80,
        loadScore: 75,
        recencyScore: 90,
        totalScore: 87,
        reasons: [
          "Strong ownership of payment-related code.",
          "High match with payment and transaction changes.",
          "Strong historical review performance.",
          "Recently reviewed related payment changes.",
        ],
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
        totalScore: 85,
        reasons: [
          "Strong backend and transaction expertise.",
          "Currently has high availability.",
          "Low current review load.",
        ],
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
        totalScore: 73,
        reasons: [
          "Good backend expertise.",
          "Has recently worked on related services.",
          "Moderate current review load.",
        ],
      },
    ];
  }
}