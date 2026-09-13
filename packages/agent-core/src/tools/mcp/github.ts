import { createMCPClient, type MCPTransportConfig } from "./client.js";

export async function createGitHubMCPClient() {
  const token = process.env.GITHUB_TOKEN;

  if (!token) {
    throw new Error("GITHUB_TOKEN is not configured.");
  }

  const config: MCPTransportConfig = {
    type: "stdio",
    command: process.env.MCP_GITHUB_COMMAND ?? "docker",
    args: [
      "run",
      "-i",
      "--rm",
      "-e",
      "GITHUB_PERSONAL_ACCESS_TOKEN",
      "-e",
      "GITHUB_TOOLSETS",
      "-e",
      "GITHUB_READ_ONLY",
      process.env.MCP_GITHUB_IMAGE ??
        "ghcr.io/github/github-mcp-server:latest",
    ],
    env: {
      GITHUB_PERSONAL_ACCESS_TOKEN: token,
      GITHUB_TOOLSETS:
        process.env.GITHUB_TOOLSETS ??
        "context,repos,pull_requests,issues",
      GITHUB_READ_ONLY: process.env.GITHUB_READ_ONLY ?? "0",
    },
  };

  return createMCPClient(
    "parallax-github-mcp-client",
    "0.1.0",
    config,
  );
}
