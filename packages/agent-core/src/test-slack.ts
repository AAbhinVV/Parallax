const token = process.env.SLACK_BOT_TOKEN;

if (!token) {
  throw new Error("SLACK_BOT_TOKEN is not configured.");
}

const response = await fetch("https://slack.com/api/auth.test", {
  headers: {
    Authorization: `Bearer ${token}`,
  },
});

const data = await response.json();

if (!data.ok) {
  throw new Error(`Slack authentication failed: ${data.error}`);
}

console.log(JSON.stringify({
  ok: data.ok,
  team: data.team,
  user: data.user,
  user_id: data.user_id,
  team_id: data.team_id,
}, null, 2));
