import { NextResponse } from "next/server";
import { assembleBatch } from "@/lib/api/batch";
import { getActivity, getIntegrationHealth, getMissions, getStats } from "@/lib/api/server";

export const dynamic = "force-dynamic";

export async function GET() {
  const correlationId = crypto.randomUUID();
  const keys = ["stats", "missions", "activity", "integrationHealth"] as const;
  const settled = await Promise.allSettled([getStats(), getMissions(6, 0), getActivity(10, 0), getIntegrationHealth()]);
  const { data, errors, status } = assembleBatch(keys, settled);
  return NextResponse.json({ data, errors, correlationId }, { status, headers: { "Cache-Control": "no-store", "X-Correlation-ID": correlationId } });
}
