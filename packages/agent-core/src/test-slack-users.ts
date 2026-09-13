import { SlackRestTool } from "./tools/slack.js";

const slack = new SlackRestTool();
const users = await slack.listUsers();

console.log(
  JSON.stringify(
    users.map((user) => ({
      id: user.id,
      name: user.name,
      realName: user.realName,
      email: user.email,
    })),
    null,
    2,
  ),
);
