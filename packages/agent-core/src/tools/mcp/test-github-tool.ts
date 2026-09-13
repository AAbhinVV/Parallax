import { config } from "dotenv";
import { MCPGitHubTool } from "./github-tool.js";

config({ path: "mcp.env" });

const github = new MCPGitHubTool();

const repository = "iamaaryan10/ai-travel-decision-engine";
const pullNumber = 4;

console.log("Testing GitHub MCP tool...\n");

const files = await github.getPullRequestFiles(repository, pullNumber);
console.log("Changed files:");
console.log(files);

const commits = await github.getPullRequestCommits(repository, pullNumber);
console.log("\nCommits:");
console.log(commits);
