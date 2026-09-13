const baseUrl = (process.env.JIRA_BASE_URL ?? "").replace(/\/+$/, "");
const email = process.env.JIRA_EMAIL ?? "";
const apiToken = process.env.JIRA_API_TOKEN ?? "";

if (!baseUrl || !email || !apiToken) {
  throw new Error("Jira environment variables are not configured.");
}

const auth = Buffer.from(`${email}:${apiToken}`).toString("base64");

const response = await fetch(
  `${baseUrl}/rest/api/3/project/KAN`,
  {
    headers: {
      Authorization: `Basic ${auth}`,
      Accept: "application/json",
    },
  },
);

const data = await response.json();

if (!response.ok) {
  throw new Error(
    `Jira project lookup failed (${response.status}): ${JSON.stringify(data)}`,
  );
}

console.log(
  JSON.stringify(
    {
      id: data.id,
      key: data.key,
      name: data.name,
      projectTypeKey: data.projectTypeKey,
      simplified: data.simplified,
    },
    null,
    2,
  ),
);
