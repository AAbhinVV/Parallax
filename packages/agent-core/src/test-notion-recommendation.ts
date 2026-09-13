import "dotenv/config";
import { analyzeNotionDocument } from "./nodes/analyze-notion-document.js";

const result = await analyzeNotionDocument({
  mission:
    "Read the Notion policy document and determine the best action the team should take.",
  context: null,
  pr: null,
  evidence: [],
  gaps: [],
  risk: null,
  reviewEffort: null,
  reviewerCandidates: [],
  availability: [],
  reviewPlan: null,
  contextPack: null,
  policyRecommendation: null,
  proposedActions: [],
  policyDecision: null,
  executionResults: [],
  verificationResults: [],
  slackSummary: "",
  auditEvents: [],
  approvalStatus: "not_required",
  currentStep: "start",
  errors: [],
});

console.log(JSON.stringify(result, null, 2));
