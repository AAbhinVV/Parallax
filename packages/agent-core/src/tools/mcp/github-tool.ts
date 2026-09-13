import { createGitHubMCPClient } from "./github.js";
import type { PR } from "../../schemas/index.js";

export interface GitHubTool {
  getPullRequest(repository: string, pullNumber: number): Promise<PR>;
  getPullRequestFiles(repository: string, pullNumber: number): Promise<string[]>;
  getPullRequestCommits(
    repository: string,
    pullNumber: number,
  ): Promise<string[]>;
}

function parseRepository(repository: string): {
  owner: string;
  repo: string;
} {
  const cleaned = repository
    .replace(/^https?:\/\/github\.com\//, "")
    .replace(/\/+$/, "");

  const [owner, repo] = cleaned.split("/");

  if (!owner || !repo) {
    throw new Error(
      `Invalid GitHub repository format: "${repository}". Expected "owner/repo".`,
    );
  }

  return { owner, repo };
}

function extractText(result: {
  content: Array<{ type: string; text?: string }>;
}): string {
  return result.content
    .filter(
      (item): item is { type: "text"; text: string } =>
        item.type === "text" && typeof item.text === "string",
    )
    .map((item) => item.text)
    .join("\n");
}

export class MCPGitHubTool implements GitHubTool {
  async getPullRequest(
    repository: string,
    pullNumber: number,
  ): Promise<PR> {
    const { owner, repo } = parseRepository(repository);
    const client = await createGitHubMCPClient();

    try {
      const result = await client.callTool({
        name: "pull_request_read",
        arguments: {
          method: "get",
          owner,
          repo,
          pullNumber,
        },
      });

      if ("isError" in result && result.isError) {
        throw new Error("GitHub MCP failed to get pull request.");
      }

      const text = extractText(result);
      const data = JSON.parse(text) as {
        number: number;
        title: string;
        body?: string | null;
        state: "open" | "closed";
        draft?: boolean | null;
        merged?: boolean;
        html_url: string;
        user?: {
          login?: string;
        };
        head?: {
          ref?: string;
        };
        base?: {
          ref?: string;
        };
        additions?: number;
        deletions?: number;
        changed_files?: number;
      };

      let state: PR["state"];

      if (data.merged) {
        state = "merged";
      } else if (data.state === "closed") {
        state = "closed";
      } else if (data.draft) {
        state = "draft";
      } else {
        state = "ready_for_review";
      }

      return {
        id: data.number,
        title: data.title,
        description: data.body ?? "",
        repository: `${owner}/${repo}`,
        author: data.user?.login ?? "unknown",
        state,
        url: data.html_url,
        branch: data.head?.ref ?? "",
        baseBranch: data.base?.ref ?? "",
        filesChanged: data.changed_files ?? 0,
        additions: data.additions ?? 0,
        deletions: data.deletions ?? 0,
      };
    } finally {
      await client.close();
    }
  }

  async getPullRequestFiles(
    repository: string,
    pullNumber: number,
  ): Promise<string[]> {
    const { owner, repo } = parseRepository(repository);
    const client = await createGitHubMCPClient();

    try {
      const result = await client.callTool({
        name: "pull_request_read",
        arguments: {
          method: "get_files",
          owner,
          repo,
          pullNumber,
          perPage: 100,
        },
      });

      if ("isError" in result && result.isError) {
        throw new Error("GitHub MCP failed to get PR files.");
      }

      const text = extractText(result);

      const parsed = JSON.parse(text) as Array<{
        filename?: string;
        path?: string;
      }>;

      return parsed
        .map((file) => file.filename ?? file.path)
        .filter((file): file is string => Boolean(file));
    } finally {
      await client.close();
    }
  }

  async getPullRequestCommits(
    repository: string,
    pullNumber: number,
  ): Promise<string[]> {
    const { owner, repo } = parseRepository(repository);
    const client = await createGitHubMCPClient();

    try {
      const result = await client.callTool({
        name: "pull_request_read",
        arguments: {
          method: "get_commits",
          owner,
          repo,
          pullNumber,
          perPage: 100,
        },
      });

      if ("isError" in result && result.isError) {
        throw new Error("GitHub MCP failed to get PR commits.");
      }

      const text = extractText(result);

      const parsed = JSON.parse(text) as Array<{
        sha?: string;
        commit?: {
          message?: string;
        };
      }>;

      return parsed.map((commit) => {
        const sha = commit.sha ?? "unknown-sha";
        const message =
          commit.commit?.message?.split("\n")[0] ?? "no message";

        return `${sha} ${message}`;
      });
    } finally {
      await client.close();
    }
  }
}