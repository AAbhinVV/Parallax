import type { PR } from "../schemas/index.js";
import type { GitHubTool } from "./github.js";

export class MockGitHubTool implements GitHubTool {
  async getPullRequest(
    repository: string,
    pullRequestId: number,
  ): Promise<PR> {
    return {
      id: pullRequestId,
      title: "Add payment retry handling",
      description:
        "Adds retry handling for failed payment requests and updates transaction logic.",
      repository,
      author: "developer-1",
      state: "ready_for_review",
      url: `https://github.com/example/${repository}/pull/${pullRequestId}`,
      branch: "feature/payment-retry",
      baseBranch: "main",
      filesChanged: 8,
      additions: 210,
      deletions: 45,
    };
  }

  async getPullRequestFiles(
    _repository: string,
    _pullRequestId: number,
  ): Promise<string[]> {
    return [
      "src/payments/retry.ts",
      "src/payments/payment-service.ts",
      "src/database/transactions.ts",
      "tests/payments/retry.test.ts",
    ];
  }

  async getPullRequestCommits(
    _repository: string,
    _pullRequestId: number,
  ): Promise<string[]> {
    return [
      "Add payment retry mechanism",
      "Handle transaction rollback",
      "Add retry tests",
    ];
  }
}