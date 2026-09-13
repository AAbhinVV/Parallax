import { config } from "dotenv";
import { createGitHubMCPClient } from "./github.js";

config({ path: "mcp.env" });

const client = await createGitHubMCPClient();

const { tools } = await client.listTools();

for (const name of ["pull_request_read", "list_commits"]) {
  const tool = tools.find((t) => t.name === name);

  console.log(`\n=== ${name} ===\n`);
  console.log(JSON.stringify(tool, null, 2));
}

await client.close();
