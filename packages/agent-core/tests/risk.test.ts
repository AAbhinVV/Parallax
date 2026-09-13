import { describe, expect, it } from "vitest";

import { calculateRisk } from "../src/intelligence/risk.js";

describe("calculateRisk", () => {
  it("classifies a payment transaction PR as high risk", () => {
    const result = calculateRisk(
    {
      id: 142,
      title: "Add payment retry handling",
      description:
        "Adds retry handling for failed payment requests and updates transaction logic.",
      repository: "payments-service",
      author: "developer-1",
      state: "ready_for_review",
      url: "https://github.com/example/payments-service/pull/142",
      branch: "feature/payment-retry",
      baseBranch: "main",
      filesChanged: 8,
      additions: 210,
      deletions: 45,
    },
    [],
  );

    expect(result.level).toBe("high");
    expect(result.score).toBe(75);
    expect(result.confidence).toBe(0.85);
  });
});