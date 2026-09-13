import { describe, expect, it } from "vitest";

import { verifyActions } from "../src/nodes/verify-actions.js";

describe("verifyActions", () => {
  it("marks failed execution as unverified", async () => {
    const result = await verifyActions({
      executionResults: [
        {
          actionId: "action-calendar-review",
          success: false,
          message: "Calendar API failed.",
        },
      ],
    } as any);

    expect(result.verificationResults).toHaveLength(1);
    expect(result.verificationResults?.[0].actionId).toBe(
      "action-calendar-review",
    );
    expect(result.verificationResults?.[0].verified).toBe(false);
    expect(result.verificationResults?.[0].details).toContain(
      "Verification failed",
    );
  });
});