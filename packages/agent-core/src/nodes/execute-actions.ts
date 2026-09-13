import type { AgentStateType } from "../graph/state.js";
import type { ExecutionResult } from "../schemas/index.js";
import { JiraRestTool } from "../tools/jira.js";

/*
 * Jira is instantiated lazily so that importing this module
 * (e.g. in tests) does not require Jira credentials.
 */
let jira: JiraRestTool | null = null;

function getJiraTool(): JiraRestTool {
  jira ??= new JiraRestTool();

  return jira;
}

export async function executeActions(
  state: AgentStateType,
): Promise<Partial<AgentStateType>> {
  if (!state.policyDecision) {
    return {
      currentStep: "cross_tool_updates",
      errors: [
        "Cannot execute actions without a policy decision.",
      ],
    };
  }

  if (!state.policyDecision.allowed) {
    return {
      currentStep: "cross_tool_updates",
      errors: [
        "Actions are not allowed by policy.",
      ],
    };
  }

  if (state.approvalStatus !== "approved") {
    return {
      currentStep: "cross_tool_updates",
      errors: [
        "Actions cannot be executed until human approval is granted.",
      ],
    };
  }

  const executionResults: ExecutionResult[] = [];

  for (const action of state.proposedActions) {
    try {
      if (action.type === "jira.create_issue") {
        if (!state.policyRecommendation) {
          executionResults.push({
            actionId: action.id,
            success: false,
            message:
              "Cannot create Jira issue because no policy recommendation is available.",
          });

          continue;
        }

        const result = await getJiraTool().createIssue(
          state.policyRecommendation.suggestedJiraSummary,
          state.policyRecommendation.suggestedJiraDescription,
          action.target,
        );

        executionResults.push({
          actionId: action.id,
          success: true,
          message:
            `Created Jira issue ${result.key}: ${result.url}`,
        });

        continue;
      }

      /*
       * Existing PR actions are still not connected to real
       * external writes yet.
       */
      executionResults.push({
        actionId: action.id,
        success: true,
        message:
          `Action ${action.type} is approved but real execution is not yet implemented.`,
      });
    } catch (error) {
      executionResults.push({
        actionId: action.id,
        success: false,
        message:
          `Failed to execute ${action.type}: ${
            error instanceof Error
              ? error.message
              : String(error)
          }`,
      });
    }
  }

  return {
    currentStep: "cross_tool_updates",
    executionResults,
    proposedActions: state.proposedActions.map(
      (action) => ({
        ...action,
        status: executionResults.find(
          (result) => result.actionId === action.id,
        )?.success
          ? "completed"
          : "failed",
      }),
    ),
  };
}
