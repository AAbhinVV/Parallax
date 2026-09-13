import { Command } from "@langchain/langgraph";
import { agentGraph } from "./graph/graph.js";

const mission =
  process.argv.slice(2).join(" ").trim();

if (!mission) {
  console.error(
    'Usage: npm run run -- "your mission here"',
  );
  process.exit(1);
}

const input = {
  mission,
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
  approvalStatus: "not_required" as const,
  currentStep: "start",
  errors: [],
};

const config = {
  configurable: {
    thread_id: `mission-${Date.now()}`,
  },
};

console.log("Starting Parallax agent...\n");
console.log(`Mission: ${mission}\n`);

const firstState = await agentGraph.invoke(
  input,
  config,
);

console.log(
  "Current step:",
  firstState.currentStep,
);

console.log(
  "Proposed actions:",
  JSON.stringify(
    firstState.proposedActions,
    null,
    2,
  ),
);

console.log("\nWaiting for PM approval...\n");

/*
 * TEMPORARY DEMO BEHAVIOUR
 *
 * This keeps our local end-to-end test moving.
 * In the real application, the frontend/backend will
 * provide the PM's decision and resume this thread.
 */
const finalState = await agentGraph.invoke(
  new Command({
    resume: "approved",
  }),
  config,
);

console.log(
  "\nFinal state:\n",
  JSON.stringify(finalState, null, 2),
);
