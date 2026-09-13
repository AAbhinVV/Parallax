import "server-only";

import { cookies } from "next/headers";

import type { TokenResponse } from "@/lib/api/types";
import { sessionCookies } from "@/lib/auth/constants";

export { sessionCookies } from "@/lib/auth/constants";

const secure = process.env.NODE_ENV === "production";

export async function readTokenCookies() {
  const store = await cookies();
  return {
    accessToken: store.get(sessionCookies.access)?.value,
    refreshToken: store.get(sessionCookies.refresh)?.value,
    workspaceId: store.get(sessionCookies.workspace)?.value,
    expiresAt: Number(store.get(sessionCookies.expires)?.value || 0),
  };
}

export async function setTokenCookies(tokens: TokenResponse) {
  const store = await cookies();
  const expiresAt = Date.now() + tokens.expires_in * 1000;
  const base = { httpOnly: true, sameSite: "lax" as const, secure, path: "/", priority: "high" as const };
  store.set(sessionCookies.access, tokens.access_token, { ...base, maxAge: tokens.expires_in });
  store.set(sessionCookies.refresh, tokens.refresh_token, base);
  store.set(sessionCookies.workspace, tokens.workspace_id, base);
  store.set(sessionCookies.expires, String(expiresAt), base);
}

export async function clearTokenCookies() {
  const store = await cookies();
  for (const name of Object.values(sessionCookies)) store.set(name, "", { httpOnly: true, sameSite: "lax", secure, path: "/", maxAge: 0 });
}
