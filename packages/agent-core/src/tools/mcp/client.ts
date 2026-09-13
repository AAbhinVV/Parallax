import {
  Client,
  StreamableHTTPClientTransport,
} from "@modelcontextprotocol/client";
import { StdioClientTransport } from "@modelcontextprotocol/client/stdio";

export type MCPTransportConfig =
  | {
      type: "stdio";
      command: string;
      args?: string[];
      env?: Record<string, string>;
    }
  | {
      type: "http";
      url: string;
      headers?: Record<string, string>;
    };

export async function createMCPClient(
  name: string,
  version: string,
  config: MCPTransportConfig,
): Promise<Client> {
  const client = new Client({
    name,
    version,
  });

  if (config.type === "stdio") {
    const transport = new StdioClientTransport({
      command: config.command,
      args: config.args,
      env: Object.fromEntries(
        Object.entries({
          ...process.env,
          ...config.env,
        }).filter(
          (entry): entry is [string, string] => entry[1] !== undefined,
        ),
      ),
    });

    await client.connect(transport);
    return client;
  }

  const transport = new StreamableHTTPClientTransport(
    new URL(config.url),
    {
      requestInit: {
        headers: config.headers,
      },
    },
  );

  await client.connect(transport);
  return client;
}
