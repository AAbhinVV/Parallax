import type { AgentStateType } from "../graph/state.js";
import type { Evidence } from "../schemas/index.js";
import { MCPGitHubTool } from "../tools/mcp/github-tool.js";
import { JiraRestTool } from "../tools/jira.js";
import { MockNotionTool } from "../tools/mock-notion.js";

/*
 * Tools are instantiated lazily so importing this module (e.g. when the
 * HTTP server boots) does not require integration credentials.
 */
let github: MCPGitHubTool | null = null;
let jira: JiraRestTool | null = null;
let notion: MockNotionTool | null = null;

function getGithubTool(): MCPGitHubTool {
  github ??= new MCPGitHubTool();

  return github;
}

function getJiraTool(): JiraRestTool {
  jira ??= new JiraRestTool();

  return jira;
}

function getNotionTool(): MockNotionTool {
  notion ??= new MockNotionTool();

  return notion;
}

export async function gatherContext(
  state: AgentStateType,
): Promise<Partial<AgentStateType>> {
  if (!state.pr) {
    return {
      currentStep: "gather_context",
      errors: ["Cannot gather context without a pull request."],
    };
  }

  try {
    const files = await getGithubTool().getPullRequestFiles(
      state.pr.repository,
      state.pr.id,
    );

    const commits = await getGithubTool().getPullRequestCommits(
      state.pr.repository,
      state.pr.id,
    );

    const jiraText = [
      state.pr.title,
      state.pr.description,
      state.pr.branch,
    ].join("\n");

    const jiraIssueKey = getJiraTool().extractIssueKey(jiraText);

    const evidence: Evidence[] = [
      {
        source: "github",
        type: "changed_files",
        title: "Changed files",
        content: files.join("\n"),
        url: state.pr.url,
      },
      {
        source: "github",
        type: "commits",
        title: "Pull request commits",
        content: commits.join("\n"),
        url: state.pr.url,
      },
    ];

    if (jiraIssueKey) {
      const jiraIssue = await getJiraTool().getIssue(jiraIssueKey);
      evidence.push(jiraIssue);
    }

    const notionContext = await getNotionTool().getProjectContext(
      "payments-reliability",
    );

    evidence.push(notionContext);

    return {
      currentStep: "gather_context",
      evidence,
    };
  } catch (error) {
    return {
      currentStep: "gather_context",
      errors: [
        `Failed to gather context: ${
          error instanceof Error ? error.message : String(error)
        }`,
      ],
    };
  }
}