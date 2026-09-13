import type { PR } from "../schemas/index.js";

export interface GitHubTool {
  getPullRequest(
    repository: string,
    pullRequestId: number,
  ): Promise<PR>;

  getPullRequestFiles(
    repository: string,
    pullRequestId: number,
  ): Promise<string[]>;

  getPullRequestCommits(
    repository: string,
    pullRequestId: number,
  ): Promise<string[]>;
}