import { config } from "dotenv";

config({ path: "mcp.env" });

const token = process.env.NOTION_API_KEY;

if (!token) {
  throw new Error("NOTION_API_KEY is not configured.");
}

const pageId = "037c217a1d264997b53070ecf6baf992";

const response = await fetch(
  `https://api.notion.com/v1/pages/${pageId}`,
  {
    headers: {
      Authorization: `Bearer ${token}`,
      "Notion-Version": "2022-06-28",
      Accept: "application/json",
    },
  },
);

const text = await response.text();

console.log("HTTP status:", response.status);
console.log(text);
