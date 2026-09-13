import { describe, expect, it } from "vitest";

import { auditActions } from "../src/nodes/audit-actions.js";

describe("auditActions", () => {
  it("creates audit events for executed actions", async () => {
    const result = await auditActions({
      proposedActions: [
        {
          id: "action-calendar-review",
          type: "calendar.create_review_block",
          target: "reviewer-1",
          reason: "Reserve review time.",
          requiresApproval: true,
          status: "completed",
        },
      ],
      executionResults: [
        {
          actionId: "action-calendar-review",
          success: true,
          message: "Calendar block created.",
        },
      ],
    } as any);

    expect(result.auditEvents).toHaveLength(1);
    expect(result.auditEvents?.[0].actionId).toBe(
      "action-calendar-review",
    );
    expect(result.auditEvents?.[0].success).toBe(true);
    expect(result.auditEvents?.[0].action).toBe(
      "calendar.create_review_block",
    );
  });
});