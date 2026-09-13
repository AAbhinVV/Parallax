import type {
  ActionProposal,
  AuditEvent,
  ContextPack,
  ExecutionResult,
  GapMismatch,
  PR,
  RiskAssessment,
  VerificationResult,
} from "./index.js";

export interface DemoResult {
  mission: string;

  pr: PR | null;

  gaps: GapMismatch[];

  currentStep: string;

  risk: {
    level: RiskAssessment["level"];
    score: number;
    confidence: number;
    explanation: string;
  };

  reviewer: {
    id: string;
    name: string;
    score: number;
    reasons: string[];
  };

  review: {
    estimatedMinutes: number;
    suggestedStart: string;
    suggestedEnd: string;
    focusAreas: string[];
    reasoning: string;
  };

  contextPack: ContextPack | null;

  actions: ActionProposal[];

  policy: {
    allowed: boolean;
    requiresApproval: boolean;
    reason: string;
  };

  execution: ExecutionResult[];

  verification: VerificationResult[];

  slackSummary: string;

  audit: AuditEvent[];

  approvalStatus:
    | "not_required"
    | "pending"
    | "approved"
    | "rejected";
}