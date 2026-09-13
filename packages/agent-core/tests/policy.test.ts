import { describe, expect, it } from "vitest";

import { evaluateActionPolicy } from "../src/policy/policy-engine.js";
import type {
  ActionProposal,
  RiskAssessment,
} from "../src/schemas/index.js";

describe("evaluateActionPolicy", () => {
  const highRisk: RiskAssessment = {
    score: 75,
    level: "high",
    confidence: 0.85,
    categories: ["payments", "data", "api", "rollback"],
    signals: [],
    explanation: "High-risk payment transaction changes.",
  };

  const action: ActionProposal = {
    id: "action-calendar-review",
    type: "create_review_block",
    target: "reviewer-1",
    reason: "Reserve review time.",
    requiresApproval: false,
    status: "proposed",
  };

  it("requires approval for high-risk actions", () => {
    const decision = evaluateActionPolicy(action, highRisk);

    expect(decision.allowed).toBe(true);
    expect(decision.requiresApproval).toBe(true);
    expect(decision.reason).toContain("High-risk");
  });
});