import { config } from "dotenv";

config({ path: "mcp.env" });

const token = process.env.NOTION_API_KEY;

if (!token) {
  throw new Error("NOTION_API_KEY is not configured.");
}

const response = await fetch("https://api.notion.com/v1/search", {
  method: "POST",
  headers: {
    Authorization: `Bearer ${token}`,
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json",
  },
  body: JSON.stringify({
    page_size: 20,
  }),
});

const text = await response.text();

console.log("HTTP status:", response.status);
console.log(text);
