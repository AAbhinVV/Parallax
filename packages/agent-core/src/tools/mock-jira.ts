import type { Evidence } from "../schemas/index.js";

export interface JiraTool {
  getIssue(issueKey: string): Promise<Evidence>;
}

export class MockJiraTool implements JiraTool {
  async getIssue(issueKey: string): Promise<Evidence> {
    return {
      source: "jira",
      type: "issue",
      title: `Jira issue ${issueKey}`,
      content:
        "Implement reliable payment retry handling with transaction rollback and idempotency safeguards.",
      url: `https://jira.example.com/browse/${issueKey}`,
    };
  }
}