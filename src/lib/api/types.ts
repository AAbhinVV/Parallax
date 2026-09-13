import type { components } from "@/generated/openapi";

export type ApiSchemas = components["schemas"];
export type Mission = ApiSchemas["MissionRead"];
export type MissionStatus = ApiSchemas["MissionStatus"];
export type MissionStep = ApiSchemas["MissionStepRead"];
export type MissionCreate = ApiSchemas["MissionCreate"];
export type DashboardStats = ApiSchemas["DashboardStatsRead"];
export type ActivityItem = ApiSchemas["ActivityRead"];
export type Project = ApiSchemas["ProjectRead"];
export type Integration = ApiSchemas["IntegrationStatusRead"];
export type IntegrationHealth = ApiSchemas["IntegrationHealthRead"];
export type IntegrationCapabilities = ApiSchemas["IntegrationCapabilitiesRead"];
export type TimelineEvent = ApiSchemas["TimelineEventRead"];
export type MissionSla = ApiSchemas["MissionSLARead"];
export type ContextPack = ApiSchemas["ContextPackRead"];
export type Assessment = ApiSchemas["AgentAssessmentRead"];
export type ApprovalBundle = ApiSchemas["ApprovalBundleRead"];
export type ApprovalDecision = ApiSchemas["ApprovalDecisionRequest"];
export type ApprovalEdit = ApiSchemas["ApprovalEditRequest"];
export type Execution = ApiSchemas["ExecutionRead"];
export type AuditEvent = ApiSchemas["AuditEventRead"];
export type AnalyticsOverview = ApiSchemas["AnalyticsOverviewRead"];
export type Member = ApiSchemas["MemberRead"];
export type WorkspaceRole = ApiSchemas["WorkspaceRole"];
export type MeResponse = ApiSchemas["MeResponse"];
export type Workspace = ApiSchemas["WorkspaceRead"];
export type WorkspaceSummary = ApiSchemas["WorkspaceSummary"];
export type TokenResponse = ApiSchemas["TokenResponse"];
export type IntegrationProvider = ApiSchemas["IntegrationProvider"];
export type ReadyResponse = ApiSchemas["ReadyResponse"];
export type HealthResponse = ApiSchemas["HealthResponse"];

export const terminalMissionStatuses = new Set<MissionStatus>([
  "completed",
  "blocked",
  "rejected",
  "cancelled",
  "partially_complete",
  "failed",
]);

export const canManage = (role: WorkspaceRole) => process.env.PARALLAX_DISABLE_RBAC === "true" || role === "owner" || role === "admin" || role === "manager";

export function normalizeDate(value: string) {
  return /(?:Z|[+-]\d{2}:?\d{2})$/.test(value) ? value : `${value}Z`;
}
