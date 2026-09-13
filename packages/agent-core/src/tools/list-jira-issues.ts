import { config } from "dotenv";

config({ path: "mcp.env" });

const baseUrl = (process.env.JIRA_BASE_URL ?? "").replace(/\/+$/, "");
const email = process.env.JIRA_EMAIL ?? "";
const apiToken = process.env.JIRA_API_TOKEN ?? "";

const credentials = Buffer.from(`${email}:${apiToken}`).toString("base64");

const jql = "created >= -365d ORDER BY created DESC";

const response = await fetch(
  `${baseUrl}/rest/api/3/search/jql?jql=${encodeURIComponent(jql)}&maxResults=20&fields=summary,status,description`,
  {
    headers: {
      Authorization: `Basic ${credentials}`,
      Accept: "application/json",
    },
  },
);

const text = await response.text();

console.log("HTTP status:", response.status);
console.log(text);
