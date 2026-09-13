import type { AgentStateType } from "../graph/state.js";
import type { ActionProposal } from "../schemas/index.js";

export async function proposeActions(
  state: AgentStateType,
): Promise<Partial<AgentStateType>> {
  const actions: ActionProposal[] = [];

  /*
   * Notion → Gemini policy mission
   *
   * The reasoning node has already produced a structured
   * recommendation that should become a proposed Jira task.
   */
  if (state.policyRecommendation) {
    actions.push({
      id: "action-jira-create",
      type: "jira.create_issue",
      target: "KAN",
      reason:
        state.policyRecommendation.recommendation,
      requiresApproval: true,
      status: "proposed",
    });

    return {
      currentStep: "propose_actions",
      proposedActions: actions,
    };
  }

  /*
   * Existing PR workflow
   */
  const jiraEvidence = state.evidence.find(
    (item) =>
      item.source === "jira" &&
      item.type === "issue",
  );

  if (jiraEvidence) {
    actions.push({
      id: "action-jira-update",
      type: "jira.update_issue",
      target: jiraEvidence.title.replace(
        /^Jira issue /,
        "",
      ),
      reason:
        `Update the linked Jira issue with the verified review outcome and identified gaps for PR ${
          state.pr?.id ?? "unknown"
        }.`,
      requiresApproval: true,
      status: "proposed",
    });
  }

  if (state.pr) {
    actions.push({
      id: "action-github-update",
      type: "github.update_pull_request",
      target: state.pr.url,
      reason:
        `Update PR ${state.pr.id} with the approved review status and relevant findings.`,
      requiresApproval: true,
      status: "proposed",
    });
  }

  const notionEvidence = state.evidence.find(
    (item) =>
      item.source === "notion" &&
      item.type === "project_context",
  );

  if (notionEvidence) {
    actions.push({
      id: "action-notion-update",
      type: "notion.update_documentation",
      target: notionEvidence.title,
      reason:
        `Finalize project documentation with the verified review outcome and cross-tool updates for PR ${
          state.pr?.id ?? "unknown"
        }.`,
      requiresApproval: true,
      status: "proposed",
    });
  }

  return {
    currentStep: "propose_actions",
    proposedActions: actions,
  };
}