import type { AgentStateType } from "../graph/state.js";
import type { VerificationResult } from "../schemas/index.js";
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

export async function verifyActions(
  state: AgentStateType,
): Promise<Partial<AgentStateType>> {
  if (state.executionResults.length === 0) {
    return {
      currentStep: "verify_actions",
      errors: [
        "Cannot verify actions because no actions were executed.",
      ],
    };
  }

  const verificationResults: VerificationResult[] = [];

  for (const result of state.executionResults) {
    if (!result.success) {
      verificationResults.push({
        actionId: result.actionId,
        verified: false,
        details:
          `Verification failed because execution failed: ${result.message}`,
      });

      continue;
    }

    /*
     * Real verification for Jira creation.
     */
    const jiraMatch = result.message.match(
      /Created Jira issue ([A-Z][A-Z0-9]*-\d+)/,
    );

    if (jiraMatch) {
      const issueKey = jiraMatch[1];

      try {
        const issue = await getJiraTool().getIssue(issueKey);

        verificationResults.push({
          actionId: result.actionId,
          verified: true,
          details:
            `Verified Jira issue ${issueKey} exists: ${issue.title}`,
        });
      } catch (error) {
        verificationResults.push({
          actionId: result.actionId,
          verified: false,
          details:
            `Jira verification failed for ${issueKey}: ${
              error instanceof Error
                ? error.message
                : String(error)
            }`,
        });
      }

      continue;
    }

    /*
     * Non-Jira actions are not yet backed by real external
     * verification.
     */
    verificationResults.push({
      actionId: result.actionId,
      verified: true,
      details:
        `Execution reported success for ${result.actionId}; no real external verification is implemented for this action yet.`,
    });
  }

  return {
    currentStep: "verify_actions",
    verificationResults,
  };
}