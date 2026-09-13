import { config } from "dotenv";
import { NotionRestTool } from "./notion.js";

config({ path: "mcp.env" });

const notion = new NotionRestTool();

const pageId = "037c217a-1d26-4997-b530-70ecf6baf992";

const result = await notion.getPageContent(pageId);

console.log(JSON.stringify(result, null, 2));
