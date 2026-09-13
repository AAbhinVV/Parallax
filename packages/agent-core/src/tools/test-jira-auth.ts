import { config } from "dotenv";

config({ path: "mcp.env" });

const baseUrl = (process.env.JIRA_BASE_URL ?? "").replace(/\/+$/, "");
const email = process.env.JIRA_EMAIL ?? "";
const apiToken = process.env.JIRA_API_TOKEN ?? "";

const credentials = Buffer.from(`${email}:${apiToken}`).toString("base64");

const response = await fetch(`${baseUrl}/rest/api/3/myself`, {
  headers: {
    Authorization: `Basic ${credentials}`,
    Accept: "application/json",
  },
});

const text = await response.text();

console.log("HTTP status:", response.status);
console.log("Content-Type:", response.headers.get("content-type"));
console.log(text);
