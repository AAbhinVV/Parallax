const baseUrl = (process.env.JIRA_BASE_URL ?? "").replace(/\/+$/, "");
const email = process.env.JIRA_EMAIL ?? "";
const apiToken = process.env.JIRA_API_TOKEN ?? "";

if (!baseUrl || !email || !apiToken) {
  throw new Error("Jira environment variables are not configured.");
}

const auth = Buffer.from(`${email}:${apiToken}`).toString("base64");

const response = await fetch(
  `${baseUrl}/rest/api/3/issue/createmeta/KAN/issuetypes`,
  {
    headers: {
      Authorization: `Basic ${auth}`,
      Accept: "application/json",
    },
  },
);

const data = await response.json();

console.log(
  JSON.stringify(
    data,
    null,
    2,
  ),
);
