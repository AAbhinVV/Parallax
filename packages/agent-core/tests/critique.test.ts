import { describe, expect, it } from "vitest";

import { critiqueActions } from "../src/nodes/critique-actions.js";

describe("critiqueActions", () => {
  it("passes valid proposed actions without errors", async () => {
    const result = await critiqueActions({
      proposedActions: [
        {
          id: "action-1",
          type: "calendar.create_review_block",
          target: "reviewer-1",
          reason: "Reserve time for PR review.",
          requiresApproval: false,
          status: "proposed",
        },
      ],
      verificationResults: [],
    } as any);

    expect(result.errors).toEqual([]);
    expect(result.currentStep).toBe("critique_actions");
  });

  it("flags failed verification", async () => {
    const result = await critiqueActions({
      proposedActions: [
        {
          id: "action-1",
          type: "calendar.create_review_block",
          target: "reviewer-1",
          reason: "Reserve time for PR review.",
          requiresApproval: false,
          status: "proposed",
        },
      ],
      verificationResults: [
        {
          actionId: "action-1",
          verified: false,
          details: "Verification failed.",
        },
      ],
    } as any);

    expect(result.errors?.[0]).toContain(
      "Verification failed for action-1",
    );
  });
});