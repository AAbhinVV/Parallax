import type { AgentStateType } from "../graph/state.js";
import { SlackRestTool } from "../tools/slack.js";

/*
 * Slack is instantiated lazily so that importing this module
 * (e.g. in tests) does not require Slack credentials.
 */
let slack: SlackRestTool | null = null;

function getSlackTool(): SlackRestTool {
  slack ??= new SlackRestTool();

  return slack;
}

const NOTIFICATION_USER_ID = "U0BN25MRDJP";

export async function buildSlackSummary(
  state: AgentStateType,
): Promise<Partial<AgentStateType>> {
  if (state.verificationResults.length === 0) {
    return {
      currentStep: "slack_summary",
      errors: [
        "Cannot send Slack notification because there are no verification results.",
      ],
    };
  }

  const failed = state.verificationResults.filter(
    (result) => !result.verified,
  );

  if (failed.length > 0) {
    return {
      currentStep: "slack_summary",
      errors: [
        `Slack notification blocked because ${failed.length} action(s) failed verification.`,
      ],
    };
  }

  const recommendation = state.policyRecommendation;

  const summary = recommendation
    ? [
        "Parallax verified action summary",
        "",
        `Recommended action: ${recommendation.recommendation}`,
        "",
        `Rationale: ${recommendation.rationale}`,
        "",
        "Jira task:",
        recommendation.suggestedJiraSummary,
        "",
        "Verification:",
        ...state.verificationResults.map(
          (result) =>
            `✓ ${result.actionId}: ${result.details}`,
        ),
      ].join("\n")
    : [
        "Parallax verified action summary",
        "",
        ...state.verificationResults.map(
          (result) =>
            `✓ ${result.actionId}: ${result.details}`,
        ),
      ].join("\n");

  try {
    await getSlackTool().sendDirectMessage(
      NOTIFICATION_USER_ID,
      summary,
    );

    return {
      currentStep: "slack_summary",
      slackSummary: summary,
    };
  } catch (error) {
    return {
      currentStep: "slack_summary",
      errors: [
        `Failed to send Slack notification: ${
          error instanceof Error
            ? error.message
            : String(error)
        }`,
      ],
    };
  }
}