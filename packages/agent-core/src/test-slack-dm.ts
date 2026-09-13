import { SlackRestTool } from "./tools/slack.js";

const slack = new SlackRestTool();

const result = await slack.sendDirectMessage(
  "U0BN25MRDJP",
  "Parallax integration test: the agent successfully sent a direct Slack notification.",
);

console.log("Message sent:", result);
