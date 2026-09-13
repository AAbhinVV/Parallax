import {
  END,
  MemorySaver,
  START,
  StateGraph,
} from "@langchain/langgraph";

import { AgentState } from "./state.js";

import { understandPR } from "../nodes/understand-pr.js";
import { gatherContext } from "../nodes/gather-context.js";
import { analyzeRisk } from "../nodes/analyze-risk.js";
import { reasonAboutRisk } from "../nodes/reason-risk.js";
import { rankReviewers } from "../nodes/rank-reviewers.js";
import { checkAvailability } from "../nodes/check-availability.js";
import { buildReviewPlan } from "../nodes/build-review-plan.js";
import { buildContextPack } from "../nodes/build-context-pack.js";
import { proposeActions } from "../nodes/propose-actions.js";
import { evaluatePolicy } from "../nodes/evaluate-policy.js";
import { executeActions } from "../nodes/execute-actions.js";
import { approvalGate } from "../nodes/approval-gate.js";
import { verifyActions } from "../nodes/verify-actions.js";
import { auditActions } from "../nodes/audit-actions.js";
import { detectGaps } from "../nodes/detect-gaps.js";
import { buildSlackSummary } from "../nodes/slack-summary.js";
import { finalizeNotionDocumentation } from "../nodes/finalize-notion.js";
import { analyzeNotionDocument } from "../nodes/analyze-notion-document.js";

export const agentGraph = new StateGraph(AgentState)
  /* ---------------------------------------------------------------------- */
  /* Nodes                                                                   */
  /* ---------------------------------------------------------------------- */

  .addNode("understand_pr", understandPR)
  .addNode("gather_context", gatherContext)
  .addNode("detect_gaps", detectGaps)
  .addNode("analyze_risk", analyzeRisk)
  .addNode("reason_risk", reasonAboutRisk)
  .addNode("rank_reviewers", rankReviewers)
  .addNode("check_availability", checkAvailability)
  .addNode("build_review_plan", buildReviewPlan)
  .addNode("build_context_pack", buildContextPack)

  .addNode(
    "analyze_notion_document",
    analyzeNotionDocument,
  )

  .addNode("propose_actions", proposeActions)
  .addNode("evaluate_policy", evaluatePolicy)
  .addNode("cross_tool_updates", executeActions)
  .addNode("approval_gate", approvalGate)
  .addNode("verify_actions", verifyActions)
  .addNode("slack_summary", buildSlackSummary)
  .addNode(
    "finalize_notion",
    finalizeNotionDocumentation,
  )
  .addNode("audit_actions", auditActions)

  /* ---------------------------------------------------------------------- */
  /* Entry point                                                             */
  /* ---------------------------------------------------------------------- */

  .addConditionalEdges(
    START,
    (state) => (state.pr ? "pr" : "notion"),
    {
      pr: "understand_pr",
      notion: "analyze_notion_document",
    },
  )

  /* ---------------------------------------------------------------------- */
  /* Existing PR workflow                                                    */
  /* ---------------------------------------------------------------------- */

  .addEdge("understand_pr", "gather_context")
  .addEdge("gather_context", "detect_gaps")
  .addEdge("detect_gaps", "analyze_risk")
  .addEdge("analyze_risk", "reason_risk")
  .addEdge("reason_risk", "rank_reviewers")
  .addEdge("rank_reviewers", "check_availability")
  .addEdge("check_availability", "build_review_plan")
  .addEdge("build_review_plan", "build_context_pack")
  .addEdge("build_context_pack", "propose_actions")

  /* ---------------------------------------------------------------------- */
  /* Notion workflow enters the same proposal/policy/approval pipeline       */
  /* ---------------------------------------------------------------------- */

  .addEdge(
    "analyze_notion_document",
    "propose_actions",
  )

  /* ---------------------------------------------------------------------- */
  /* Shared action pipeline                                                  */
  /* ---------------------------------------------------------------------- */

  .addEdge("propose_actions", "evaluate_policy")
  .addEdge("evaluate_policy", "approval_gate")

  .addConditionalEdges(
    "approval_gate",
    (state) =>
      state.approvalStatus === "approved"
        ? "execute"
        : "wait",
    {
      execute: "cross_tool_updates",
      wait: END,
    },
  )

  .addEdge(
    "cross_tool_updates",
    "verify_actions",
  )

  .addConditionalEdges(
    "verify_actions",
    (state) =>
      state.verificationResults.length > 0 &&
      state.verificationResults.every(
        (result) => result.verified,
      )
        ? "slack_summary"
        : "evaluate_policy",
    {
      slack_summary: "slack_summary",
      evaluate_policy: "evaluate_policy",
    },
  )

  /* ---------------------------------------------------------------------- */
  /* Finalization                                                            */
  /* ---------------------------------------------------------------------- */

  .addEdge(
    "slack_summary",
    "finalize_notion",
  )

  .addEdge(
    "finalize_notion",
    "audit_actions",
  )

  .addEdge("audit_actions", END)

  .compile({
    checkpointer: new MemorySaver(),
  });