"use server";

import { redirect } from "next/navigation";

import { createBackendClient, unwrap } from "@/lib/api/client";
import { ApiError } from "@/lib/api/errors";
import { clearTokenCookies, readTokenCookies, setTokenCookies } from "@/lib/auth/cookies";

export type AuthActionState = { error?: string; correlationId?: string; fields?: Record<string, string> };

function value(formData: FormData, name: string) {
  return String(formData.get(name) || "").trim();
}

export async function loginAction(_: AuthActionState, formData: FormData): Promise<AuthActionState> {
  const email = value(formData, "email");
  const password = value(formData, "password");
  const workspaceId = value(formData, "workspace_id") || undefined;
  if (!email || !password) return { error: "Email and password are required.", fields: { email, workspace_id: workspaceId || "" } };
  try {
    const tokens = unwrap(await createBackendClient().POST("/api/auth/login", { body: { email, password, workspace_id: workspaceId } }));
    await setTokenCookies(tokens);
  } catch (error) {
    if (error instanceof ApiError) return { error: error.message, correlationId: error.correlationId, fields: { email, workspace_id: workspaceId || "" } };
    return { error: "The API could not be reached.", fields: { email, workspace_id: workspaceId || "" } };
  }
  redirect("/dashboard");
}

export async function registerAction(_: AuthActionState, formData: FormData): Promise<AuthActionState> {
  const body = {
    email: value(formData, "email"),
    password: value(formData, "password"),
    display_name: value(formData, "display_name"),
    workspace_name: value(formData, "workspace_name"),
    workspace_slug: value(formData, "workspace_slug"),
  };
  if (!body.email || body.password.length < 12 || !body.display_name || !body.workspace_name || !body.workspace_slug) {
    return { error: "Complete every field. Passwords require at least 12 characters.", fields: { ...body, password: "" } };
  }
  try {
    const tokens = unwrap(await createBackendClient().POST("/api/auth/register", { body }));
    await setTokenCookies(tokens);
  } catch (error) {
    if (error instanceof ApiError) return { error: error.message, correlationId: error.correlationId, fields: { ...body, password: "" } };
    return { error: "The API could not be reached.", fields: { ...body, password: "" } };
  }
  redirect("/dashboard");
}

export async function logoutAction() {
  const tokens = await readTokenCookies();
  try {
    if (tokens.refreshToken) {
      await createBackendClient(tokens.accessToken, tokens.workspaceId).POST("/api/auth/logout", { body: { refresh_token: tokens.refreshToken } });
    }
  } finally {
    await clearTokenCookies();
  }
  redirect("/login");
}
