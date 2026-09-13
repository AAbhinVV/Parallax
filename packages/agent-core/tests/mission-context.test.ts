import { describe, expect, it } from "vitest";

import { renderKnowledgeBase } from "../src/reasoning/system-prompt.js";
import type { MissionContext } from "../src/types/mission-context.js";

/**
 * Canonical backend-shaped context: exactly what `build_mission_context()`
 * in `app/services/knowledge.py` emits as the `knowledge_base` field of the
 * backend's AgentContextRequest. The agent contract must accept this shape
 * unchanged.
 */
const backendContext: MissionContext = {
  task: "Create the Jira task from the policy brief and notify the team.",
  mission_status: "running",
  result_summary: null,
  facts: [
    {
      id: "6f1d2c8e-0000-4000-8000-000000000001",
      kind: "source_fact",
      source: "jira",
      source_ref: "KAN-5",
      fact: "KAN-5: Issue status is Done",
      data: { key: "jira:KAN-5", url: null },
      observed_at: "2026-09-13T19:42:10+00:00",
      verified_at: "2026-09-13T19:43:00+00:00",
      status: "verified",
      confidence: null,
    },
    {
      id: "6f1d2c8e-0000-4000-8000-000000000002",
      kind: "source_fact",
      source: "slack",
      source_ref: "msg-9",
      fact: "No completion message found",
      data: { conflict_reason: "Contradicts verified Jira state" },
      observed_at: "2026-09-13T19:44:00+00:00",
      verified_at: null,
      status: "conflicted",
      confidence: null,
    },
  ],
  decisions: [
    {
      id: "6f1d2c8e-0000-4000-8000-000000000003",
      kind: "decision",
      source: "agent",
      source_ref: "agent-run:1",
      fact: "Team notification required",
      data: {
        context_summary: "Policy brief requires a Jira task and team notification",
        risk_level: "medium",
        proposals: ["jira:issue.create"],
      },
      observed_at: "2026-09-13T19:45:00+00:00",
      verified_at: null,
      status: "observed",
      confidence: 0.94,
    },
  ],
  recent_actions: [
    {
      id: "6f1d2c8e-0000-4000-8000-000000000004",
      provider: "jira",
      operation: "issue.create",
      rationale: "Create the policy task",
      status: "approved",
      execution_status: "verified",
      external_id: "KAN-5",
      verification_status: "verified",
    },
  ],
  pending_actions: [
    {
      id: "6f1d2c8e-0000-4000-8000-000000000005",
      provider: "slack",
      operation: "message.post",
      rationale: "Notify the team channel",
      status: "proposed",
    },
  ],
  verified_outcomes: [
    {
      id: "6f1d2c8e-0000-4000-8000-000000000004",
      provider: "jira",
      operation: "issue.create",
      rationale: "Create the policy task",
      status: "approved",
      execution_status: "verified",
      external_id: "KAN-5",
      verification_status: "verified",
    },
  ],
  conflicts: [
    {
      id: "6f1d2c8e-0000-4000-8000-000000000002",
      kind: "source_fact",
      source: "slack",
      source_ref: "msg-9",
      fact: "No completion message found",
      data: { conflict_reason: "Contradicts verified Jira state" },
      observed_at: "2026-09-13T19:44:00+00:00",
      verified_at: null,
      status: "conflicted",
      confidence: null,
    },
  ],
};

describe("MissionContext contract", () => {
  it("accepts a full backend context pack and renders it", () => {
    const output = renderKnowledgeBase(backendContext);

    expect(output).toContain("Mission status:\nrunning");
    expect(output).toContain("Result summary:\nNone");
    expect(output).toContain(
      "[jira:KAN-5]\nKAN-5: Issue status is Done\nStatus: verified",
    );
    expect(output).toContain("jira.issue.create -> KAN-5");
  });

  it("keeps derived decisions distinguishable from source facts", () => {
    const output = renderKnowledgeBase(backendContext);

    const factsSection = output.indexOf("VERIFIED SOURCE FACTS");
    const decisionsSection = output.indexOf(
      "DERIVED DECISIONS — NOT SOURCE TRUTH",
    );

    expect(decisionsSection).toBeGreaterThan(factsSection);
    expect(output.indexOf("KAN-5: Issue status is Done")).toBeLessThan(
      decisionsSection,
    );
    expect(output).toContain("(confidence 0.94) Team notification required");
  });

  it("surfaces conflicts with their reason", () => {
    const output = renderKnowledgeBase(backendContext);

    expect(output).toContain("CONFLICTS");
    expect(output).toContain("No completion message found");
    expect(output).toContain("Reason: Contradicts verified Jira state");
    expect(output).toContain("- Contradicts verified Jira state");
  });

  it("accepts a fresh mission with no knowledge yet", () => {
    const output = renderKnowledgeBase({
      task: "Create the Jira task from the policy brief.",
      mission_status: "context_collected",
      result_summary: null,
      facts: [],
      decisions: [],
      recent_actions: [],
      pending_actions: [],
      verified_outcomes: [],
      conflicts: [],
    });

    expect(output).toContain("Mission status:\ncontext_collected");
    expect(output).toContain("VERIFIED SOURCE FACTS\n\nNone.");
    expect(output).toContain("DERIVED DECISIONS — NOT SOURCE TRUTH\n\nNone.");
  });
});
