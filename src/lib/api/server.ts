import "server-only";

import { redirect } from "next/navigation";

import { createBackendClient, unwrap } from "@/lib/api/client";
import { ApiError } from "@/lib/api/errors";
import type { ApprovalDecision, ApprovalEdit, IntegrationProvider, MissionCreate, WorkspaceRole } from "@/lib/api/types";
import { clearTokenCookies, readTokenCookies, setTokenCookies } from "@/lib/auth/cookies";
import { authDisabled, previewSession } from "@/lib/auth/preview";

async function authenticatedClient() {
  const tokens = await readTokenCookies();
  const accessToken = tokens.accessToken || (authDisabled ? process.env.PARALLAX_DEV_ACCESS_TOKEN : undefined);
  const workspaceId = tokens.workspaceId || (authDisabled ? process.env.PARALLAX_DEV_WORKSPACE_ID : undefined);
  if (!accessToken && !authDisabled) throw new ApiError("Authentication required.", 401);
  return createBackendClient(accessToken, workspaceId);
}

async function actionCall<T>(operation: (client: ReturnType<typeof createBackendClient>) => Promise<{ data?: T; error?: unknown; response: Response }>) {
  let tokens = await readTokenCookies();
  const accessToken = tokens.accessToken || (authDisabled ? process.env.PARALLAX_DEV_ACCESS_TOKEN : undefined);
  const workspaceId = tokens.workspaceId || (authDisabled ? process.env.PARALLAX_DEV_WORKSPACE_ID : undefined);
  if (!accessToken && !authDisabled) throw new ApiError("Authentication required.", 401);
  let result = await operation(createBackendClient(accessToken, workspaceId));
  if (result.response.status === 401 && tokens.refreshToken) {
    try {
      const refreshClient = createBackendClient();
      const refreshed = unwrap(await refreshClient.POST("/api/auth/refresh", { body: { refresh_token: tokens.refreshToken } }));
      await setTokenCookies(refreshed);
    } catch (error) {
      if (error instanceof ApiError && error.status === 401) await clearTokenCookies();
      throw error;
    }
    tokens = await readTokenCookies();
    result = await operation(createBackendClient(tokens.accessToken, tokens.workspaceId));
  }
  return unwrap(result);
}

export async function requireSession() {
  if (authDisabled) {
    try {
      const client = await authenticatedClient();
      const me = unwrap(await client.GET("/api/auth/me"));
      return { ...me, expiresAt: (await readTokenCookies()).expiresAt };
    } catch {
      return previewSession;
    }
  }
  try {
    const client = await authenticatedClient();
    const me = unwrap(await client.GET("/api/auth/me"));
    const expiresAt = (await readTokenCookies()).expiresAt;
    return { ...me, expiresAt };
  } catch (error) {
    if (error instanceof ApiError && error.status === 401) redirect("/login");
    throw error;
  }
}

export async function getStats() { const c = await authenticatedClient(); return unwrap(await c.GET("/api/dashboard/stats")); }
export async function getActivity(limit = 10, offset = 0) { const c = await authenticatedClient(); return unwrap(await c.GET("/api/dashboard/activity", { params: { query: { limit, offset } } })); }
export async function getProjects() { const c = await authenticatedClient(); return unwrap(await c.GET("/api/dashboard/projects")); }
export async function getIntegrations() { const c = await authenticatedClient(); return unwrap(await c.GET("/api/integrations")); }
export async function getIntegrationHealth() { const c = await authenticatedClient(); return unwrap(await c.GET("/api/integrations/health")); }
export async function getIntegrationCapabilities(provider: IntegrationProvider) { const c = await authenticatedClient(); return unwrap(await c.GET("/api/integrations/{provider}/capabilities", { params: { path: { provider } } })); }
export async function getMissions(limit = 20, offset = 0) { const c = await authenticatedClient(); return unwrap(await c.GET("/api/missions", { params: { query: { limit, offset } } })); }
export async function getMission(id: string) { const c = await authenticatedClient(); return unwrap(await c.GET("/api/missions/{mission_id}", { params: { path: { mission_id: id } } })); }
export async function getTimeline(id: string) { const c = await authenticatedClient(); return unwrap(await c.GET("/api/missions/{mission_id}/timeline", { params: { path: { mission_id: id } } })); }
export async function getSla(id: string) { const c = await authenticatedClient(); return unwrap(await c.GET("/api/missions/{mission_id}/sla", { params: { path: { mission_id: id } } })); }
export async function getContextPack(id: string) { const c = await authenticatedClient(); return unwrap(await c.GET("/api/missions/{mission_id}/context-pack", { params: { path: { mission_id: id } } })); }
export async function getAssessment(id: string) { const c = await authenticatedClient(); return unwrap(await c.GET("/api/missions/{mission_id}/assessment", { params: { path: { mission_id: id } } })); }
export async function getExecutions(id: string) { const c = await authenticatedClient(); return unwrap(await c.GET("/api/missions/{mission_id}/executions", { params: { path: { mission_id: id } } })); }
export async function getApproval(id: string) { const c = await authenticatedClient(); return unwrap(await c.GET("/api/approvals/{bundle_id}", { params: { path: { bundle_id: id } } })); }
export async function getAuditEvents(query: { mission_id?: string; event_type?: string; limit?: number; offset?: number }) { const c = await authenticatedClient(); return unwrap(await c.GET("/api/audit-events", { params: { query } })); }
export async function getAnalytics() { const c = await authenticatedClient(); return unwrap(await c.GET("/api/analytics/overview")); }
export async function getMembers() { const c = await authenticatedClient(); return unwrap(await c.GET("/api/workspaces/current/members")); }
export async function getCurrentWorkspace() { const c = await authenticatedClient(); return unwrap(await c.GET("/api/workspaces/current")); }
export async function getHealth() { return unwrap(await createBackendClient().GET("/health")); }
export async function getApiHealth() { return unwrap(await createBackendClient().GET("/api/health")); }
export async function getReady() { return unwrap(await createBackendClient().GET("/ready")); }

export async function createMission(body: MissionCreate, idempotencyKey: string) { return actionCall((c) => c.POST("/api/missions", { body, params: { header: { "Idempotency-Key": idempotencyKey } } })); }
export async function cancelMission(id: string) { return actionCall((c) => c.POST("/api/missions/{mission_id}/cancel", { params: { path: { mission_id: id } } })); }
export async function retryMission(id: string) { return actionCall((c) => c.POST("/api/missions/{mission_id}/retry", { params: { path: { mission_id: id } } })); }
export async function prepareApproval(id: string) { return actionCall((c) => c.POST("/api/missions/{mission_id}/approval", { params: { path: { mission_id: id } } })); }
export async function approveBundle(id: string, body: ApprovalDecision) { return actionCall((c) => c.POST("/api/approvals/{bundle_id}/approve", { params: { path: { bundle_id: id } }, body })); }
export async function rejectBundle(id: string, body: ApprovalDecision) { return actionCall((c) => c.POST("/api/approvals/{bundle_id}/reject", { params: { path: { bundle_id: id } }, body })); }
export async function cancelBundle(id: string, body: ApprovalDecision) { return actionCall((c) => c.POST("/api/approvals/{bundle_id}/cancel", { params: { path: { bundle_id: id } }, body })); }
export async function editBundle(id: string, body: ApprovalEdit) { return actionCall((c) => c.POST("/api/approvals/{bundle_id}/edit", { params: { path: { bundle_id: id } }, body })); }
export async function checkIntegration(provider: IntegrationProvider) { return actionCall((c) => c.POST("/api/integrations/{provider}/check", { params: { path: { provider } } })); }
export async function updateMemberRole(userId: string, role: WorkspaceRole) { return actionCall((c) => c.PATCH("/api/workspaces/current/members/{user_id}", { params: { path: { user_id: userId } }, body: { role } })); }
