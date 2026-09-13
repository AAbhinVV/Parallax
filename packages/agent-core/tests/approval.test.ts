import { describe, expect, it } from "vitest";

import { approvalGate } from "../src/nodes/approval-gate.js";

describe("approvalGate", () => {
  it("pauses when human approval is required", async () => {
    const resultPromise = approvalGate({
      policyDecision: {
        allowed: true,
        requiresApproval: true,
        reason: "High-risk changes require approval.",
      },
      proposedActions: [],
      risk: {
        score: 75,
        level: "high",
        confidence: 0.85,
        categories: [],
        signals: [],
        explanation: "High-risk payment changes.",
      },
    } as any);

    await expect(resultPromise).rejects.toThrow();
  });
});