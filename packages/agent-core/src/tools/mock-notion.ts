import type { Evidence } from "../schemas/index.js";

export interface NotionTool {
  getProjectContext(projectId: string): Promise<Evidence>;
}

export class MockNotionTool implements NotionTool {
  async getProjectContext(projectId: string): Promise<Evidence> {
    return {
      source: "notion",
      type: "project_context",
      title: `Notion project context ${projectId}`,
      content:
        "Payment reliability initiative focused on resilient transaction processing and safe retry behavior.",
      url: `https://notion.example.com/project/${projectId}`,
    };
  }
}