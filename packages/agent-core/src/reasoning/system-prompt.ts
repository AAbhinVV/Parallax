export const PARALLAX_SYSTEM_PROMPT = `You are the reasoning layer of Parallax.

Your task is to analyze the task given to you by the leader,
manager, or user and determine the single best operational
action supported by the task and the available information.

Think according to the task.

Use only the sources and tools that are applicable to the task.
For example, if the task involves Jira, use Jira where applicable.
If it involves Slack, use Slack where applicable.
If it involves GitHub or Notion, use them where applicable.

Do not perform unrelated operations or invent actions that are
not supported by the task.

Parallax is one reasoning agent operating through a multi-step
workflow. Use the current task, the current knowledge base, and
fresh source information to reason about the current step.

The knowledge base is persistent operational context.

Previously stored knowledge is not automatically current truth.
Fresh verified source information takes precedence over stale
knowledge.

Source facts and agent-derived decisions are different.
A derived decision must never be treated as if it were a source fact.

When information is missing, conflicting, stale, or insufficient,
identify the uncertainty instead of guessing.

Do not invent users, issues, tickets, messages, statuses,
deadlines, requirements, actions, or outcomes.

Determine the single best operational action supported by the
current task and available evidence.`;

import type {
  KnowledgeAction,
  KnowledgeFact,
  MissionContext,
} from "../types/mission-context.js";

const CONTEXT_PRECEDENCE = `CONTEXT PRECEDENCE

1. Fresh verified source observations have highest priority.
2. Previously verified knowledge-base facts are historical operational context.
3. Agent-derived decisions are derived knowledge, not source truth.
4. When sources conflict, do not invent a reconciliation.
5. Prefer the latest verified source observation over stale knowledge and report material conflicts.`;

function renderFact(fact: KnowledgeFact): string[] {
  return [
    `[${fact.source}:${fact.source_ref}]`,
    fact.fact,
    `Status: ${fact.status}`,
    `Observed: ${fact.observed_at}`,
  ];
}

function renderOutcome(action: KnowledgeAction): string[] {
  const target = action.external_id ? ` -> ${action.external_id}` : "";
  const status =
    action.verification_status ?? action.execution_status ?? action.status;

  return [`${action.provider}.${action.operation}${target}`, `Status: ${status}`];
}

function renderPendingAction(action: KnowledgeAction): string[] {
  const target = action.external_id ? ` -> ${action.external_id}` : "";

  return [
    `${action.provider}.${action.operation}${target}`,
    `Rationale: ${action.rationale}`,
    `Status: ${action.execution_status ?? action.status}`,
  ];
}

function renderConflict(conflict: KnowledgeFact): string[] {
  const lines: string[] = [
    `[${conflict.source}:${conflict.source_ref}]`,
    conflict.fact,
    `Status: ${conflict.status}`,
  ];

  const reason = conflict.data?.conflict_reason;
  if (typeof reason === "string" && reason.length > 0) {
    lines.push(`Reason: ${reason}`);
  }

  return lines;
}

/**
 * Machine-identifiable uncertainties come from conflicted facts until the
 * backend adds a dedicated uncertainties field to the context pack.
 */
function deriveUncertainties(conflicts: KnowledgeFact[]): string[] {
  return conflicts.map((conflict) => {
    const reason = conflict.data?.conflict_reason;

    return typeof reason === "string" && reason.length > 0
      ? reason
      : `Unverified conflicting observation for ${conflict.source}:${conflict.source_ref}`;
  });
}

/**
 * Renders the mission knowledge base as bounded prompt text.
 *
 * Sections are deterministic and always present, in this order:
 * CURRENT MISSION, CONTEXT PRECEDENCE, VERIFIED SOURCE FACTS,
 * RECENT VERIFIED OUTCOMES, PENDING ACTIONS,
 * DERIVED DECISIONS - NOT SOURCE TRUTH, CONFLICTS, UNCERTAINTIES.
 *
 * Conflicted facts are rendered only in CONFLICTS (never as source facts)
 * so provenance stays unambiguous. Executed-but-unverified recent actions
 * are surfaced under PENDING ACTIONS: they still require attention.
 */
export function renderKnowledgeBase(
  context: MissionContext | null | undefined,
): string {
  if (!context) {
    return "No operational knowledge base is available.";
  }

  const lines: string[] = [];

  lines.push(
    "CURRENT MISSION",
    "",
    "Task:",
    context.task,
    "",
    "Mission status:",
    context.mission_status,
    "",
    "Result summary:",
    context.result_summary ?? "None",
    "",
  );

  lines.push(CONTEXT_PRECEDENCE, "");

  lines.push("VERIFIED SOURCE FACTS", "");
  const sourceFacts = context.facts.filter(
    (fact) => fact.status !== "conflicted",
  );
  if (sourceFacts.length > 0) {
    for (const fact of sourceFacts) {
      lines.push(...renderFact(fact), "");
    }
  } else {
    lines.push("None.", "");
  }

  lines.push("RECENT VERIFIED OUTCOMES", "");
  if (context.verified_outcomes.length > 0) {
    for (const outcome of context.verified_outcomes) {
      lines.push(...renderOutcome(outcome), "");
    }
  } else {
    lines.push("None.", "");
  }

  const verifiedIds = new Set(
    context.verified_outcomes.map((action) => action.id),
  );
  const unverifiedRecent = context.recent_actions.filter(
    (action) => !verifiedIds.has(action.id),
  );
  lines.push("PENDING ACTIONS", "");
  if (context.pending_actions.length > 0 || unverifiedRecent.length > 0) {
    for (const action of context.pending_actions) {
      lines.push(...renderPendingAction(action), "");
    }
    for (const action of unverifiedRecent) {
      lines.push(...renderPendingAction(action), "");
    }
  } else {
    lines.push("None.", "");
  }

  lines.push("DERIVED DECISIONS — NOT SOURCE TRUTH", "");
  if (context.decisions.length > 0) {
    for (const decision of context.decisions) {
      const confidence =
        decision.confidence !== null
          ? `(confidence ${decision.confidence}) `
          : "";
      lines.push(`${confidence}${decision.fact}`);
    }
    lines.push("");
  } else {
    lines.push("None.", "");
  }

  lines.push("CONFLICTS", "");
  if (context.conflicts.length > 0) {
    for (const conflict of context.conflicts) {
      lines.push(...renderConflict(conflict), "");
    }
    lines.push(
      "Use fresh verified information when determining the current state.",
      "",
    );
  } else {
    lines.push("None.", "");
  }

  lines.push("UNCERTAINTIES", "");
  const uncertainties = deriveUncertainties(context.conflicts);
  if (uncertainties.length > 0) {
    for (const uncertainty of uncertainties) {
      lines.push(`- ${uncertainty}`);
    }
  } else {
    lines.push("None.");
  }

  return `${lines.join("\n").trimEnd()}\n`;
}
