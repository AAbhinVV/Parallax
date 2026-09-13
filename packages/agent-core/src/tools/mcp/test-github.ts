import { config } from "dotenv";
import { createGitHubMCPClient } from "./github.js";

config({ path: "mcp.env" });

const client = await createGitHubMCPClient();

const result = await client.callTool({
  name: "list_pull_requests",
  arguments: {
    owner: "iamaaryan10",
    repo: "ai-travel-decision-engine",
    state: "all",
    perPage: 10,
  },
});

console.log(JSON.stringify(result, null, 2));

await client.close();
