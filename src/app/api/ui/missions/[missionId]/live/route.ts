import { NextRequest, NextResponse } from "next/server";
import { assembleBatch } from "@/lib/api/batch";
import { getApproval, getAssessment, getContextPack, getExecutions, getMission, getSla, getTimeline } from "@/lib/api/server";

export const dynamic = "force-dynamic";

export async function GET(request: NextRequest, { params }: { params: Promise<{ missionId: string }> }) {
  const { missionId } = await params; const approvalId = request.nextUrl.searchParams.get("approvalId"); const correlationId = crypto.randomUUID();
  const entries: Array<[string, Promise<unknown>]> = [["mission", getMission(missionId)], ["timeline", getTimeline(missionId)], ["sla", getSla(missionId)], ["executions", getExecutions(missionId)], ["contextPack", getContextPack(missionId)], ["assessment", getAssessment(missionId)]];
  if (approvalId) entries.push(["approval", getApproval(approvalId)]);
  const settled = await Promise.allSettled(entries.map(([, promise]) => promise));
  const { data, errors, status } = assembleBatch(entries.map(([key]) => key), settled);
  return NextResponse.json({ data, errors, correlationId }, { status, headers: { "Cache-Control": "no-store", "X-Correlation-ID": correlationId } });
}
