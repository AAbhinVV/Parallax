import { GoogleGenAI } from "@google/genai";
import type { BaseMessage } from "@langchain/core/messages";

import type { ModelGateway } from "./model-gateway.js";
import "dotenv/config";

export class GeminiGateway implements ModelGateway {
  private readonly client: GoogleGenAI;
  private readonly model: string;

  constructor() {
    const apiKey = process.env.GEMINI_API_KEY;

    if (!apiKey) {
      throw new Error("GEMINI_API_KEY is not set.");
    }

    this.client = new GoogleGenAI({
      apiKey,
    });

    this.model = process.env.GEMINI_MODEL ?? "gemini-3.6-flash";
  }

  async invoke(messages: BaseMessage[]): Promise<string> {
    const systemMessages: string[] = [];
    const userMessages: string[] = [];

    for (const message of messages) {
      const content =
        typeof message.content === "string"
          ? message.content
          : JSON.stringify(message.content);

      if (message.getType() === "system") {
        systemMessages.push(content);
      } else {
        userMessages.push(content);
      }
    }

    const response = await this.client.models.generateContent({
      model: this.model,
      contents: userMessages.join("\n\n"),
      config: {
        systemInstruction: systemMessages.join("\n\n"),
        temperature: 0,
      },
    });

    return response.text ?? "";
  }
}