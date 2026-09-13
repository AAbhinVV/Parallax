import { config } from "dotenv";
import { createGitHubMCPClient } from "./github.js";

config({ path: "mcp.env" });

const client = await createGitHubMCPClient();

const result = await client.callTool({
  name: "get_file_contents",
  arguments: {
    owner: "iamaaryan10",
    repo: "ai-travel-decision-engine",
    path: "",
  },
});

console.log(JSON.stringify(result, null, 2));

await client.close();
