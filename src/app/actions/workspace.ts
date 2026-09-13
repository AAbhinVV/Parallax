"use server";
import { revalidatePath } from "next/cache";
import { checkIntegration, updateMemberRole } from "@/lib/api/server";
import type { IntegrationProvider, WorkspaceRole } from "@/lib/api/types";
import { ApiError } from "@/lib/api/errors";
import type { MutationState } from "@/app/actions/missions";

const failure = (error: unknown): MutationState => error instanceof ApiError ? { error: error.message, correlationId: error.correlationId } : { error: "The request could not be completed." };

export async function checkIntegrationAction(provider: IntegrationProvider, state: MutationState, formData: FormData): Promise<MutationState> { void state; void formData; try { await checkIntegration(provider); } catch (error) { return failure(error); } revalidatePath("/integrations"); return {}; }
export async function updateRoleAction(userId: string, _: MutationState, formData: FormData): Promise<MutationState> { const role = String(formData.get("role")) as WorkspaceRole; if (!["owner", "admin", "manager", "reviewer", "viewer"].includes(role)) return { error: "Select a valid workspace role." }; try { await updateMemberRole(userId, role); } catch (error) { return failure(error); } revalidatePath("/team"); return {}; }
