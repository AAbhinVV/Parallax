"use server";

import { redirect } from "next/navigation";

import { ApiError } from "@/lib/api/errors";
import { approveBundle, cancelBundle, cancelMission, createMission, editBundle, prepareApproval, rejectBundle, retryMission } from "@/lib/api/server";
import type { ApprovalEdit } from "@/lib/api/types";

export type MutationState = { error?: string; correlationId?: string };
const failure = (error: unknown): MutationState => error instanceof ApiError ? { error: error.message, correlationId: error.correlationId } : { error: "The request could not be completed." };

export async function createMissionAction(_: MutationState, formData: FormData): Promise<MutationState> {
  const prompt = String(formData.get("prompt") || "").trim();
  const project = String(formData.get("project") || "").trim() || "General";
  const idempotencyKey = String(formData.get("idempotency_key") || crypto.randomUUID());
  if (prompt.length < 3 || prompt.length > 10_000) return { error: "Mission instructions must contain 3–10,000 characters." };
  let mission;
  try { mission = await createMission({ prompt, project }, idempotencyKey); } catch (error) { return failure(error); }
  redirect(`/missions/${mission.id}`);
}

export async function cancelMissionAction(id: string, state: MutationState, formData: FormData): Promise<MutationState> { void state; void formData; try { await cancelMission(id); } catch (error) { return failure(error); } redirect(`/missions/${id}`); }
export async function retryMissionAction(id: string, state: MutationState, formData: FormData): Promise<MutationState> { void state; void formData; try { await retryMission(id); } catch (error) { return failure(error); } redirect(`/missions/${id}`); }
export async function prepareApprovalAction(id: string, state: MutationState, formData: FormData): Promise<MutationState> { void state; void formData; let approval; try { approval = await prepareApproval(id); } catch (error) { return failure(error); } redirect(`/missions/${id}?approvalId=${approval.id}`); }

async function decide(kind: "approve" | "reject" | "cancel", missionId: string, bundleId: string, formData: FormData): Promise<MutationState> {
  const body = { note: String(formData.get("note") || "").trim() || undefined };
  try {
    if (kind === "approve") await approveBundle(bundleId, body);
    else if (kind === "reject") await rejectBundle(bundleId, body);
    else await cancelBundle(bundleId, body);
  } catch (error) { return failure(error); }
  redirect(`/missions/${missionId}?approvalId=${bundleId}`);
}

export async function approveBundleAction(missionId: string, bundleId: string, _: MutationState, formData: FormData) { return decide("approve", missionId, bundleId, formData); }
export async function rejectBundleAction(missionId: string, bundleId: string, _: MutationState, formData: FormData) { return decide("reject", missionId, bundleId, formData); }
export async function cancelBundleAction(missionId: string, bundleId: string, _: MutationState, formData: FormData) { return decide("cancel", missionId, bundleId, formData); }
export async function editBundleAction(missionId: string, bundleId: string, _: MutationState, formData: FormData): Promise<MutationState> {
  let actions: ApprovalEdit["actions"];
  try { actions = JSON.parse(String(formData.get("actions") || "[]")) as ApprovalEdit["actions"]; }
  catch { return { error: "Proposed actions must be valid JSON." }; }
  const providers = new Set(["github", "jira", "notion", "slack"]);
  const valid = Array.isArray(actions) && actions.every((item) => item && providers.has(item.provider) && typeof item.operation === "string" && typeof item.rationale === "string" && Array.isArray(item.citations));
  if (!valid) return { error: "Every action requires a supported provider, operation, rationale, and citations array." };
  try { await editBundle(bundleId, { actions, note: String(formData.get("note") || "").trim() || undefined }); }
  catch (error) { return failure(error); }
  redirect(`/missions/${missionId}?approvalId=${bundleId}`);
}
