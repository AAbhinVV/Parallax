import { z } from "zod";

export const ReasoningStatusSchema = z.enum([
  "action_required",
  "already_completed",
  "needs_clarification",
  "no_action_required",
]);

export type ReasoningStatus = z.infer<typeof ReasoningStatusSchema>;

export const PolicyRecommendationSchema = z.object({
  recommendation: z.string(),
  rationale: z.string(),
  suggestedJiraSummary: z.string(),
  suggestedJiraDescription: z.string(),
  status: ReasoningStatusSchema.default("action_required"),
  confidence: z.number().min(0).max(1).optional(),
  uncertainties: z.array(z.string()).default([]),
  evidence: z.array(z.string()).default([]),
});

export type PolicyRecommendation = z.infer<
  typeof PolicyRecommendationSchema
>;
