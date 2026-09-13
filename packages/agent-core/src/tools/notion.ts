import type { Evidence } from "../schemas/index.js";

export interface NotionTool {
  getPageContent(pageId: string): Promise<Evidence>;
  extractPageId(text: string): string | null;
}

type RichText = {
  plain_text?: string;
};

type NotionBlock = {
  type: string;
  [key: string]: unknown;
};

export function extractNotionPageId(
  text: string,
): string | null {
  const urlMatch = text.match(
    /notion\.com\/(?:p\/)?[^ \t\r\n]*?([a-f0-9]{32})/i,
  );

  if (urlMatch?.[1]) {
    return urlMatch[1];
  }

  const idMatch = text.match(
    /(?:^|[^a-f0-9])([a-f0-9]{32})(?:[^a-f0-9]|$)/i,
  );

  return idMatch?.[1] ?? null;
}

export class NotionRestTool implements NotionTool {
  private readonly token: string;

  constructor() {
    this.token = process.env.NOTION_API_KEY ?? "";

    if (!this.token) {
      throw new Error(
        "NOTION_API_KEY is not configured.",
      );
    }
  }

  private async request<T>(
    url: string,
  ): Promise<T> {
    const response = await fetch(url, {
      headers: {
        Authorization: `Bearer ${this.token}`,
        "Notion-Version": "2022-06-28",
        Accept: "application/json",
      },
    });

    if (!response.ok) {
      const body = await response.text();

      throw new Error(
        `Notion API request failed (${response.status}): ${body}`,
      );
    }

    return (await response.json()) as T;
  }

  extractPageId(text: string): string | null {
    return extractNotionPageId(text);
  }

  private extractRichText(
    value: unknown,
  ): string {
    if (!Array.isArray(value)) {
      return "";
    }

    return value
      .map(
        (item) =>
          (item as RichText).plain_text ?? "",
      )
      .join("");
  }

  private extractBlockText(
    block: NotionBlock,
  ): string {
    const type = block.type;

    const data = block[type] as
      | {
          rich_text?: unknown;
        }
      | undefined;

    if (!data?.rich_text) {
      return "";
    }

    return this.extractRichText(
      data.rich_text,
    );
  }

  async getPageContent(
    pageId: string,
  ): Promise<Evidence> {
    const page = await this.request<{
      id: string;
      url?: string;
      properties?: {
        title?: {
          title?: RichText[];
        };
      };
    }>(
      `https://api.notion.com/v1/pages/${pageId}`,
    );

    const blocksResponse =
      await this.request<{
        results: NotionBlock[];
        has_more: boolean;
        next_cursor: string | null;
      }>(
        `https://api.notion.com/v1/blocks/${pageId}/children?page_size=100`,
      );

    const content =
      blocksResponse.results
        .map((block) => {
          const text =
            this.extractBlockText(block);

          if (!text) {
            return "";
          }

          switch (block.type) {
            case "heading_1":
            case "heading_2":
            case "heading_3":
              return `\n${text}\n`;

            case "bulleted_list_item":
              return `- ${text}`;

            case "numbered_list_item":
              return `1. ${text}`;

            case "callout":
              return `> ${text}`;

            default:
              return text;
          }
        })
        .filter(Boolean)
        .join("\n");

    const title =
      this.extractRichText(
        page.properties?.title?.title,
      ) || "Untitled Notion page";

    return {
      source: "notion",
      type: "page",
      title,
      content,
      url: page.url,
    };
  }
}