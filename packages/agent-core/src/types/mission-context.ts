/**
 * Mission knowledge base types — the wire contract between the backend and
 * the Parallax agent. This is the ONLY context representation the agent
 * receives from the backend.
 *
 * Shape mirrors `build_mission_context()` in `app/services/knowledge.py`
 * 1:1 (snake_case keys). It reaches agent-core as the `knowledge_base`
 * field of the backend's AgentContextRequest and flows through
 * AgentState.context as runtime data only — the knowledge base itself
 * lives in the backend (PostgreSQL); AgentState must not accumulate
 * long-term knowledge.
 *
 * Size is bounded by the backend (per-source caps, verified-first selection,
 * limited decisions/actions): the backend decides what context is relevant;
 * the agent decides what that context means.
 *
 * Two knowledge kinds are strictly separated:
 * - source_fact: what an integration actually returned (observed knowledge)
 * - decision:    what the agent concluded (derived knowledge, never source truth)
 */

export type KnowledgeFactKind = "source_fact" | "decision";

export type KnowledgeSource = "github" | "jira" | "notion" | "slack" | "agent";

export type KnowledgeFactStatus =
  | "observed"
  | "verified"
  | "superseded"
  | "conflicted";

export interface KnowledgeFact {
  id: string;
  kind: KnowledgeFactKind;
  source: KnowledgeSource;
  source_ref: string;
  fact: string;
  observed_at: string;
  verified_at: string | null;
  status: KnowledgeFactStatus;
  confidence: number | null;
  data: Record<string, unknown>;
}

export interface KnowledgeAction {
  id: string;
  provider: string;
  operation: string;
  rationale: string;
  status: string;
  execution_status?: string;
  external_id?: string | null;
  verification_status?: string;
}

/**
 * Bounded read-model the agent receives on every call:
 * current task + latest knowledge + action state + conflicts.
 */
export interface MissionContext {
  task: string;
  mission_status: string;
  result_summary: string | null;
  facts: KnowledgeFact[];
  decisions: KnowledgeFact[];
  recent_actions: KnowledgeAction[];
  pending_actions: KnowledgeAction[];
  verified_outcomes: KnowledgeAction[];
  conflicts: KnowledgeFact[];
}
