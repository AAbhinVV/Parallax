export interface SlackUser {
  id: string;
  name: string;
  realName: string;
  email?: string;
}

export interface SlackTool {
  listUsers(): Promise<SlackUser[]>;
  findUser(nameOrEmail: string): Promise<SlackUser | null>;
  sendDirectMessage(
    userId: string,
    message: string,
  ): Promise<{
    channel: string;
    timestamp: string;
  }>;
}

export class SlackRestTool implements SlackTool {
  private readonly token: string;

  constructor() {
    this.token = process.env.SLACK_BOT_TOKEN ?? "";

    if (!this.token) {
      throw new Error("SLACK_BOT_TOKEN is not configured.");
    }
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {},
  ): Promise<T> {
    const response = await fetch(`https://slack.com/api/${endpoint}`, {
      ...options,
      headers: {
        Authorization: `Bearer ${this.token}`,
        "Content-Type": "application/json",
        ...(options.headers ?? {}),
      },
    });

    const data = (await response.json()) as {
      ok: boolean;
      error?: string;
    } & T;

    if (!response.ok || !data.ok) {
      throw new Error(
        `Slack API request failed: ${data.error ?? response.statusText}`,
      );
    }

    return data;
  }

  async listUsers(): Promise<SlackUser[]> {
    const data = await this.request<{
      members?: Array<{
        id?: string;
        name?: string;
        real_name?: string;
        profile?: {
          real_name?: string;
          email?: string;
        };
        deleted?: boolean;
        is_bot?: boolean;
      }>;
    }>("users.list");

    return (data.members ?? [])
      .filter(
        (user) =>
          user.id &&
          !user.deleted &&
          !user.is_bot,
      )
      .map((user) => ({
        id: user.id!,
        name: user.name ?? "",
        realName:
          user.profile?.real_name ??
          user.real_name ??
          "",
        email: user.profile?.email,
      }));
  }

  async findUser(nameOrEmail: string): Promise<SlackUser | null> {
    const users = await this.listUsers();
    const query = nameOrEmail.trim().toLowerCase();

    return (
      users.find(
        (user) =>
          user.name.toLowerCase() === query ||
          user.realName.toLowerCase() === query ||
          user.email?.toLowerCase() === query,
      ) ?? null
    );
  }

  async sendDirectMessage(
    userId: string,
    message: string,
  ): Promise<{
    channel: string;
    timestamp: string;
  }> {
    const data = await this.request<{
      channel?: string;
      ts?: string;
    }>("chat.postMessage", {
      method: "POST",
      body: JSON.stringify({
        channel: userId,
        text: message,
      }),
    });

    if (!data.channel || !data.ts) {
      throw new Error(
        "Slack API response did not contain channel or timestamp.",
      );
    }

    return {
      channel: data.channel,
      timestamp: data.ts,
    };
  }
}
