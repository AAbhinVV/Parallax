import type { Evidence } from "../schemas/index.js";

export interface JiraTool {
  getIssue(issueKey: string): Promise<Evidence>;
  extractIssueKey(text: string): string | null;
  createIssue(
    summary: string,
    description: string,
    projectKey: string,
  ): Promise<{
    key: string;
    id: string;
    url: string;
  }>;
}

export class JiraRestTool implements JiraTool {
  private readonly baseUrl: string;
  private readonly email: string;
  private readonly apiToken: string;

  constructor() {
    this.baseUrl = (process.env.JIRA_BASE_URL ?? "").replace(/\/+$/, "");
    this.email = process.env.JIRA_EMAIL ?? "";
    this.apiToken = process.env.JIRA_API_TOKEN ?? "";

    if (!this.baseUrl) {
      throw new Error("JIRA_BASE_URL is not configured.");
    }

    if (!this.email) {
      throw new Error("JIRA_EMAIL is not configured.");
    }

    if (!this.apiToken) {
      throw new Error("JIRA_API_TOKEN is not configured.");
    }
  }

  private getAuthHeader(): string {
    return `Basic ${Buffer.from(
      `${this.email}:${this.apiToken}`,
    ).toString("base64")}`;
  }

  extractIssueKey(text: string): string | null {
    const match = text.match(/\b[A-Z][A-Z0-9]*-\d+\b/);
    return match?.[0] ?? null;
  }

  async getIssue(issueKey: string): Promise<Evidence> {
    const response = await fetch(
      `${this.baseUrl}/rest/api/3/issue/${encodeURIComponent(issueKey)}`,
      {
        method: "GET",
        headers: {
          Authorization: this.getAuthHeader(),
          Accept: "application/json",
        },
      },
    );

    if (!response.ok) {
      const body = await response.text();

      throw new Error(
        `Jira API request failed (${response.status}): ${body}`,
      );
    }

    const data = (await response.json()) as {
      key: string;
      fields?: {
        summary?: string;
        description?: unknown;
      };
      self?: string;
    };

    const description =
      typeof data.fields?.description === "string"
        ? data.fields.description
        : JSON.stringify(data.fields?.description ?? "");

    return {
      source: "jira",
      type: "issue",
      title: data.fields?.summary ?? `Jira issue ${data.key}`,
      content: description,
      url: data.self
        ? data.self.replace("/rest/api/3/issue/", "/browse/")
        : `${this.baseUrl}/browse/${data.key}`,
    };
  }

  async createIssue(
    summary: string,
    description: string,
    projectKey: string,
  ): Promise<{
    key: string;
    id: string;
    url: string;
  }> {
    const response = await fetch(
      `${this.baseUrl}/rest/api/3/issue`,
      {
        method: "POST",
        headers: {
          Authorization: this.getAuthHeader(),
          Accept: "application/json",
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          fields: {
            project: {
              key: projectKey,
            },
            summary,
            description: {
              type: "doc",
              version: 1,
              content: [
                {
                  type: "paragraph",
                  content: [
                    {
                      type: "text",
                      text: description,
                    },
                  ],
                },
              ],
            },
            issuetype: {
              id: "10009",
            },
          },
        }),
      },
    );

    if (!response.ok) {
      const body = await response.text();

      throw new Error(
        `Jira create issue failed (${response.status}): ${body}`,
      );
    }

    const data = (await response.json()) as {
      id: string;
      key: string;
      self?: string;
    };

    return {
      id: data.id,
      key: data.key,
      url: data.self
        ? data.self.replace("/rest/api/3/issue/", "/browse/")
        : `${this.baseUrl}/browse/${data.key}`,
    };
  }
}

