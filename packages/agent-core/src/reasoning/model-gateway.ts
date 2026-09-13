import type { BaseMessage } from "@langchain/core/messages";

export interface ModelGateway {
  invoke(messages: BaseMessage[]): Promise<string>;
}