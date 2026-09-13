import { describe, expect, it } from "vitest";

import {
  PARALLAX_SYSTEM_PROMPT,
  renderKnowledgeBase,
} from "../src/reasoning/system-prompt.js";
import type { MissionContext } from "../src/types/mission-context.js";

function buildContext(): MissionContext {
  return {
    task: "Review payment PR and synchronize tracking",
    mission_status: "running",
    result_summary: null,
    facts: [
      {
        id: "f-1",
        kind: "source_fact",
        source: "jira",
        source_ref: "PAY-18",
        fact: "PAY-18 is Done",
        data: {},
        observed_at: "2026-09-13T10:30:00Z",
        verified_at: "2026-09-13T10:31:00Z",
        status: "verified",
        confidence: null,
      },
      {
        id: "f-2",
        kind: "source_fact",
        source: "notion",
        source_ref: "037c",
        fact: "Policy brief recommends an AIA process",
        data: {},
        observed_at: "2026-09-13T10:29:00Z",
        verified_at: null,
        status: "observed",
        confidence: null,
      },
    ],
    decisions: [
      {
        id: "d-1",
        kind: "decision",
        source: "agent",
        source_ref: "agent-run:1",
        fact: "Team notification required",
        data: {},
        observed_at: "2026-09-13T10:32:00Z",
        verified_at: null,
        status: "observed",
        confidence: 0.94,
      },
    ],
    recent_actions: [
      {
        id: "a-1",
        provider: "jira",
        operation: "issue.create",
        rationale: "Create the policy task",
        status: "approved",
        execution_status: "verified",
        external_id: "PAY-18",
        verification_status: "verified",
      },
    ],
    pending_actions: [
      {
        id: "a-2",
        provider: "slack",
        operation: "message.post",
        rationale: "Notify the project channel",
        status: "proposed",
      },
    ],
    verified_outcomes: [
      {
        id: "a-1",
        provider: "jira",
        operation: "issue.create",
        rationale: "Create the policy task",
        status: "approved",
        execution_status: "verified",
        external_id: "PAY-18",
        verification_status: "verified",
      },
    ],
    conflicts: [
      {
        id: "f-3",
        kind: "source_fact",
        source: "slack",
        source_ref: "msg-9",
        fact: "No completion message found",
        data: { conflict_reason: "Contradicts verified Jira state" },
        observed_at: "2026-09-13T10:33:00Z",
        verified_at: null,
        status: "conflicted",
        confidence: null,
      },
    ],
  };
}

describe("PARALLAX_SYSTEM_PROMPT", () => {
  it("establishes the single-agent, task-driven reasoning contract", () => {
    expect(PARALLAX_SYSTEM_PROMPT).toContain("reasoning layer of Parallax");
    expect(PARALLAX_SYSTEM_PROMPT).toContain("one reasoning agent");
    expect(PARALLAX_SYSTEM_PROMPT).toContain("applicable to the task");
    expect(PARALLAX_SYSTEM_PROMPT).toContain("knowledge base");
    expect(PARALLAX_SYSTEM_PROMPT).toContain(
      "Fresh verified source information takes precedence",
    );
    expect(PARALLAX_SYSTEM_PROMPT).toContain(
      "must never be treated as if it were a source fact",
    );
    expect(PARALLAX_SYSTEM_PROMPT).toContain("Do not invent");
    expect(PARALLAX_SYSTEM_PROMPT).toContain(
      "identify the uncertainty instead of guessing",
    );
  });

  it("does not lock reasoning to a single document or source", () => {
    expect(PARALLAX_SYSTEM_PROMPT).not.toContain("Notion document");
    expect(PARALLAX_SYSTEM_PROMPT).not.toContain("only analyze");
  });
});

describe("renderKnowledgeBase", () => {
  it("returns a deterministic fallback for null context", () => {
    expect(renderKnowledgeBase(null)).toBe(
      "No operational knowledge base is available.",
    );
  });

  it("renders all sections in the canonical order", () => {
    const output = renderKnowledgeBase(buildContext());

    let last = -1;
    for (const section of [
      "CURRENT MISSION",
      "CONTEXT PRECEDENCE",
      "VERIFIED SOURCE FACTS",
      "RECENT VERIFIED OUTCOMES",
      "PENDING ACTIONS",
      "DERIVED DECISIONS — NOT SOURCE TRUTH",
      "CONFLICTS",
      "UNCERTAINTIES",
    ]) {
      const index = output.indexOf(section);
      expect(index).toBeGreaterThan(last);
      last = index;
    }
  });

  it("renders the mission first with task, status and result summary", () => {
    const output = renderKnowledgeBase(buildContext());

    const missionSection = output.indexOf("CURRENT MISSION");
    const factsSection = output.indexOf("VERIFIED SOURCE FACTS");

    expect(output).toContain(
      "Task:\nReview payment PR and synchronize tracking",
    );
    expect(output).toContain("Mission status:\nrunning");
    expect(output).toContain("Result summary:\nNone");
    expect(missionSection).toBeLessThan(factsSection);
  });

  it("includes the context precedence rules with fresh-over-stale priority", () => {
    const output = renderKnowledgeBase(buildContext());

    expect(output).toContain("CONTEXT PRECEDENCE");
    expect(output).toContain(
      "Fresh verified source observations have highest priority",
    );
    expect(output).toContain("stale");
  });

  it("renders verified source facts with provenance", () => {
    const output = renderKnowledgeBase(buildContext());

    expect(output).toContain(
      "[jira:PAY-18]\nPAY-18 is Done\nStatus: verified",
    );
    expect(output).toContain("[notion:037c]");
    expect(output).toContain("Status: observed");
    expect(output).toContain("Observed: 2026-09-13T10:30:00Z");
  });

  it("keeps derived decisions separated from source facts", () => {
    const output = renderKnowledgeBase(buildContext());

    const factsSection = output.indexOf("VERIFIED SOURCE FACTS");
    const decisionsSection = output.indexOf(
      "DERIVED DECISIONS — NOT SOURCE TRUTH",
    );

    expect(decisionsSection).toBeGreaterThan(factsSection);
    expect(output).toContain("(confidence 0.94) Team notification required");
    expect(output.indexOf("PAY-18 is Done")).toBeLessThan(decisionsSection);
  });

  it("renders verified outcomes with their external target", () => {
    const output = renderKnowledgeBase(buildContext());

    expect(output).toContain("RECENT VERIFIED OUTCOMES");
    expect(output).toContain("jira.issue.create -> PAY-18");
    expect(output).toContain("Status: verified");
  });

  it("renders pending actions with rationale and status", () => {
    const output = renderKnowledgeBase(buildContext());

    expect(output).toContain("PENDING ACTIONS");
    expect(output).toContain("slack.message.post");
    expect(output).toContain("Rationale: Notify the project channel");
  });

  it("renders conflicts with their reason and fresh-state guidance", () => {
    const output = renderKnowledgeBase(buildContext());

    expect(output).toContain("CONFLICTS");
    expect(output).toContain("[slack:msg-9]");
    expect(output).toContain("Reason: Contradicts verified Jira state");
    expect(output).toContain(
      "Use fresh verified information when determining the current state.",
    );
  });

  it("derives uncertainties from conflicts", () => {
    const output = renderKnowledgeBase(buildContext());

    expect(output).toContain("UNCERTAINTIES");
    expect(output).toContain("- Contradicts verified Jira state");
  });

  it("renders explicit None for empty sections", () => {
    const output = renderKnowledgeBase({
      task: "Update the Jira issue.",
      mission_status: "running",
      result_summary: null,
      facts: [],
      decisions: [],
      recent_actions: [],
      pending_actions: [],
      verified_outcomes: [],
      conflicts: [],
    });

    expect(output).toContain("VERIFIED SOURCE FACTS\n\nNone.");
    expect(output).toContain("RECENT VERIFIED OUTCOMES\n\nNone.");
    expect(output).toContain("PENDING ACTIONS\n\nNone.");
    expect(output).toContain("DERIVED DECISIONS — NOT SOURCE TRUTH\n\nNone.");
    expect(output).toContain("CONFLICTS\n\nNone.");
    expect(output).toContain("UNCERTAINTIES\n\nNone.");
  });
});
