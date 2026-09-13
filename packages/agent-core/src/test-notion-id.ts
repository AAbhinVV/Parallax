import { NotionRestTool } from "./tools/notion.js";

const notion = new NotionRestTool();

const mission =
  "Read https://app.notion.com/p/Policy-Brief-Bias-in-High-Stakes-AI-Systems-037c217a1d264997b53070ecf6baf992 and suggest the best action, then notify Jira.";

console.log("Extracted page ID:");
console.log(notion.extractPageId(mission));
