import { z } from "zod";

/* -------------------------------------------------------------------------- */
/* PR                                                                         */
/* -------------------------------------------------------------------------- */

export const PRSchema = z.object({
  id: z.number(),
  title: z.string(),
  description: z.string(),
  repository: z.string(),
  author: z.string(),
  state: z.enum([
    "draft",
    "open",
    "ready_for_review",
    "closed",
    "merged",
  ]),
  url: z.string().url(),
  branch: z.string(),
  baseBranch: z.string(),
  filesChanged: z.number().default(0),
  additions: z.number().default(0),
  deletions: z.number().default(0),
});

export type PR = z.infer<typeof PRSchema>;

/* -------------------------------------------------------------------------- */
/* Evidence                                                                  */
/* -------------------------------------------------------------------------- */

export const EvidenceSchema = z.object({
  source: z.enum([
    "github",
    "jira",
    "linear",
    "notion",
    "slack",
    "calendar",
  ]),
  type: z.string(),
  title: z.string(),
  content: z.string(),
  url: z.string().optional(),
});

export type Evidence = z.infer<typeof EvidenceSchema>;

/* -------------------------------------------------------------------------- */
/* Gap & Mismatch                                                             */
/* -------------------------------------------------------------------------- */

export const GapMismatchSchema = z.object({
  type: z.enum(["gap", "mismatch"]),
  description: z.string(),
  sources: z.array(z.string()),
  severity: z.enum(["low", "medium", "high"]),
});

export type GapMismatch = z.infer<typeof GapMismatchSchema>;

/* -------------------------------------------------------------------------- */
/* Risk                                                                      */
/* -------------------------------------------------------------------------- */

export const RiskCategorySchema = z.enum([
  "security",
  "payments",
  "data",
  "api",
  "concurrency",
  "configuration",
  "infrastructure",
  "rollback",
  "change_size",
  "ownership",
  "freshness",
  "related_failures",
]);

export type RiskCategory = z.infer<typeof RiskCategorySchema>;

export const RiskSignalSchema = z.object({
  category: RiskCategorySchema,
  description: z.string(),
  score: z.number().min(0).max(100),
  evidence: z.array(EvidenceSchema),
});

export type RiskSignal = z.infer<typeof RiskSignalSchema>;

export const RiskAssessmentSchema = z.object({
  level: z.enum(["low", "medium", "high", "critical"]),
  score: z.number().min(0).max(100),
  signals: z.array(RiskSignalSchema),
  explanation: z.string(),
  confidence: z.number().min(0).max(1),
});

export type RiskAssessment = z.infer<typeof RiskAssessmentSchema>;

/* -------------------------------------------------------------------------- */
/* Review Effort                                                              */
/* -------------------------------------------------------------------------- */

export const ReviewEffortSchema = z.object({
  estimatedMinutes: z.number().positive(),
  complexity: z.enum(["small", "medium", "large", "very_large"]),
  reasoning: z.string(),
});

export type ReviewEffort = z.infer<typeof ReviewEffortSchema>;

/* -------------------------------------------------------------------------- */
/* Reviewer                                                                   */
/* -------------------------------------------------------------------------- */

export const ReviewerCandidateSchema = z.object({
  id: z.string(),
  name: z.string(),

  ownershipScore: z.number().min(0).max(100),
  skillMatchScore: z.number().min(0).max(100),
  historicalScore: z.number().min(0).max(100),
  availabilityScore: z.number().min(0).max(100),
  loadScore: z.number().min(0).max(100),
  recencyScore: z.number().min(0).max(100),

  totalScore: z.number().min(0).max(100),

  reasons: z.array(z.string()),
});

export type ReviewerCandidate = z.infer<
  typeof ReviewerCandidateSchema
>;

/* -------------------------------------------------------------------------- */
/* Availability                                                               */
/* -------------------------------------------------------------------------- */

export const AvailabilitySlotSchema = z.object({
  reviewerId: z.string(),
  start: z.string(),
  end: z.string(),
  durationMinutes: z.number().positive(),
});

export type AvailabilitySlot = z.infer<typeof AvailabilitySlotSchema>;

/* -------------------------------------------------------------------------- */
/* Review Plan                                                                */
/* -------------------------------------------------------------------------- */

export const ReviewPlanSchema = z.object({
  recommendedReviewerId: z.string(),
  recommendedReviewerName: z.string(),

  estimatedMinutes: z.number().positive(),

  suggestedStart: z.string(),
  suggestedEnd: z.string(),

  focusAreas: z.array(z.string()),

  reasoning: z.string(),
});

export type ReviewPlan = z.infer<typeof ReviewPlanSchema>;

/* -------------------------------------------------------------------------- */
/* Action                                                                     */
/* -------------------------------------------------------------------------- */

export const ActionTypeSchema = z.enum([
  "jira.create_issue",
  "jira.update_issue",
  "github.update_pull_request",
  "notion.update_documentation",
]);

export type ActionType = z.infer<typeof ActionTypeSchema>;

export const ActionProposalSchema = z.object({
  id: z.string(),
  type: ActionTypeSchema,

  target: z.string(),

  reason: z.string(),

  requiresApproval: z.boolean(),

  status: z.enum([
    "proposed",
    "approved",
    "rejected",
    "executing",
    "completed",
    "failed",
  ]),
});

export type ActionProposal = z.infer<typeof ActionProposalSchema>;

/* -------------------------------------------------------------------------- */
/* Policy                                                                     */
/* -------------------------------------------------------------------------- */

export const PolicyDecisionSchema = z.object({
  allowed: z.boolean(),
  requiresApproval: z.boolean(),
  reason: z.string(),
});

export type PolicyDecision = z.infer<typeof PolicyDecisionSchema>;

/* -------------------------------------------------------------------------- */
/* Execution                                                                  */
/* -------------------------------------------------------------------------- */

export const ExecutionResultSchema = z.object({
  actionId: z.string(),
  success: z.boolean(),
  externalId: z.string().optional(),
  message: z.string(),
});

export type ExecutionResult = z.infer<typeof ExecutionResultSchema>;

/* -------------------------------------------------------------------------- */
/* Verification                                                               */
/* -------------------------------------------------------------------------- */

export const VerificationResultSchema = z.object({
  actionId: z.string(),
  verified: z.boolean(),
  details: z.string(),
});

export type VerificationResult = z.infer<
  typeof VerificationResultSchema
>;

/* -------------------------------------------------------------------------- */
/* Audit                                                                      */
/* -------------------------------------------------------------------------- */

export const AuditEventSchema = z.object({
  actionId: z.string().optional(),
  action: z.string(),
  reason: z.string(),
  timestamp: z.string(),
  success: z.boolean(),
});

export type AuditEvent = z.infer<typeof AuditEventSchema>;

/* -------------------------------------------------------------------------- */
/* Context Pack                                                               */
/* -------------------------------------------------------------------------- */

export const ContextPackSchema = z.object({
  pr: PRSchema,

  whyThisPRExists: z.object({
    linkedIssue: z.string().optional(),
    acceptanceCriteria: z.array(z.string()),
    productContext: z.string(),
  }),

  whatChanged: z.object({
    files: z.array(z.string()),
    functionalSummary: z.string(),
    architecturalImpact: z.string(),
    dependencies: z.array(z.string()),
  }),

  risk: RiskAssessmentSchema,

  evidence: z.array(EvidenceSchema),

  reviewPlan: ReviewPlanSchema,
});

export type ContextPack = z.infer<typeof ContextPackSchema>;