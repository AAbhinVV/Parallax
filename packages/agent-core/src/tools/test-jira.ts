import { config } from "dotenv";
import { JiraRestTool } from "./jira.js";

config({ path: "mcp.env" });

const jira = new JiraRestTool();

const issueKey = "PAY-142";

console.log(`Fetching Jira issue ${issueKey}...\n`);

const issue = await jira.getIssue(issueKey);

console.log(JSON.stringify(issue, null, 2));
