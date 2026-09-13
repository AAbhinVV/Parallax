import { Annotation } from "@langchain/langgraph";

import type {
  PR,
  Evidence,
  RiskAssessment,
  ReviewEffort,
  ReviewerCandidate,
  AvailabilitySlot,
  ReviewPlan,
  ContextPack,
  ActionProposal,
  PolicyDecision,
  ExecutionResult,
  VerificationResult,
  AuditEvent,
  GapMismatch,
} from "../schemas/index.js";

import type { PolicyRecommendation } from "../schemas/policy-recommendation.js";

import type { MissionContext } from "../types/mission-context.js";

/**
 * Shared state that flows through the Parallax agent graph.
 *
 * Every node reads from this state and returns updates to it.
 */
export const AgentState = Annotation.Root({
  /* ------------------------------------------------------------------------ */
  /* Input                                                                     */
  /* ------------------------------------------------------------------------ */

  mission: Annotation<string>({
    value: (_, update) => update,
    default: () => "",
  }),

  /* ------------------------------------------------------------------------ */
  /* PR context                                                                */
  /* ------------------------------------------------------------------------ */

  pr: Annotation<PR | null>({
    value: (_, update) => update,
    default: () => null,
  }),

  /* ------------------------------------------------------------------------ */
  /* Evidence                                                                  */
  /* ------------------------------------------------------------------------ */

  evidence: Annotation<Evidence[]>({
    value: (current, update) => [...current, ...update],
    default: () => [],
  }),

  gaps: Annotation<GapMismatch[]>({
    value: (_, update) => update,
    default: () => [],
  }),

  /* ------------------------------------------------------------------------ */
  /* Intelligence                                                              */
  /* ------------------------------------------------------------------------ */

  risk: Annotation<RiskAssessment | null>({
    value: (_, update) => update,
    default: () => null,
  }),

  reviewEffort: Annotation<ReviewEffort | null>({
    value: (_, update) => update,
    default: () => null,
  }),

  /* ------------------------------------------------------------------------ */
  /* Reviewer routing                                                          */
  /* ------------------------------------------------------------------------ */

  reviewerCandidates: Annotation<ReviewerCandidate[]>({
    value: (_, update) => update,
    default: () => [],
  }),

  availability: Annotation<AvailabilitySlot[]>({
    value: (_, update) => update,
    default: () => [],
  }),

  reviewPlan: Annotation<ReviewPlan | null>({
    value: (_, update) => update,
    default: () => null,
  }),

  /* ------------------------------------------------------------------------ */
  /* Context Pack                                                              */
  /* ------------------------------------------------------------------------ */

  contextPack: Annotation<ContextPack | null>({
    value: (_, update) => update,
    default: () => null,
  }),

  /* ------------------------------------------------------------------------ */
  /* Policy Recommendation                                                     */
  /* ------------------------------------------------------------------------ */

  policyRecommendation: Annotation<PolicyRecommendation | null>({
    value: (_, update) => update,
    default: () => null,
  }),

  /* ------------------------------------------------------------------------ */
  /* Actions                                                                   */
  /* ------------------------------------------------------------------------ */

  proposedActions: Annotation<ActionProposal[]>({
    value: (_, update) => update,
    default: () => [],
  }),

  policyDecision: Annotation<PolicyDecision | null>({
    value: (_, update) => update,
    default: () => null,
  }),

  /* ------------------------------------------------------------------------ */
  /* Execution                                                                 */
  /* ------------------------------------------------------------------------ */

  executionResults: Annotation<ExecutionResult[]>({
    value: (current, update) => [...current, ...update],
    default: () => [],
  }),

  verificationResults: Annotation<VerificationResult[]>({
    value: (current, update) => [...current, ...update],
    default: () => [],
  }),

  slackSummary: Annotation<string>({
    value: (_, update) => update,
    default: () => "",
  }),

  /* ------------------------------------------------------------------------ */
  /* Audit                                                                     */
  /* ------------------------------------------------------------------------ */

  auditEvents: Annotation<AuditEvent[]>({
    value: (current, update) => [...current, ...update],
    default: () => [],
  }),

  /* ------------------------------------------------------------------------ */
  /* Control                                                                   */
  /* ------------------------------------------------------------------------ */

  /**
   * Mission knowledge base excerpt supplied by the backend on each run.
   * Runtime passthrough only — the KB itself lives in the backend;
   * AgentState must not accumulate long-term knowledge.
   */
  context: Annotation<MissionContext | null>({
    value: (_, update) => update,
    default: () => null,
  }),

  approvalStatus: Annotation<
    "not_required" | "pending" | "approved" | "rejected"
  >({
    value: (_, update) => update,
    default: () => "not_required",
  }),

  currentStep: Annotation<string>({
    value: (_, update) => update,
    default: () => "start",
  }),

  errors: Annotation<string[]>({
    value: (current, update) => [...current, ...update],
    default: () => [],
  }),
});

export type AgentStateType = typeof AgentState.State;