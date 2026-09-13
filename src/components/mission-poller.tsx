"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

import { terminalMissionStatuses, type MissionStatus } from "@/lib/api/types";
import { pollingDelay } from "@/lib/pagination";

type LiveMission = { data?: { mission?: { status?: MissionStatus } } };

export function MissionPoller({ missionId, status, approvalId }: { missionId: string; status: MissionStatus; approvalId?: string }) {
  const router = useRouter();
  useEffect(() => {
    if (terminalMissionStatuses.has(status)) return;
    let timer: ReturnType<typeof setTimeout> | undefined;
    let controller: AbortController | undefined;
    let failures = 0;
    let stopped = false;
    let inFlight = false;

    const schedule = (delay: number) => { if (!stopped) timer = setTimeout(tick, delay); };
    const tick = async () => {
      if (stopped || inFlight) return;
      if (document.hidden) { schedule(2_000); return; }
      inFlight = true;
      controller = new AbortController();
      try {
        const query = approvalId ? `?approvalId=${encodeURIComponent(approvalId)}` : "";
        const response = await fetch(`/api/ui/missions/${encodeURIComponent(missionId)}/live${query}`, { cache: "no-store", signal: controller.signal });
        if (response.status === 401) { stopped = true; router.replace("/login"); return; }
        if (response.status === 404) { stopped = true; router.refresh(); return; }
        if (!response.ok) throw new Error("Mission refresh failed");
        const payload = await response.json() as LiveMission;
        failures = 0;
        const nextStatus = payload.data?.mission?.status;
        if (nextStatus && terminalMissionStatuses.has(nextStatus)) stopped = true;
        router.refresh();
      } catch (error) { if ((error as Error).name !== "AbortError") failures += 1; }
      finally { inFlight = false; }
      schedule(pollingDelay(failures, 2_000));
    };
    const onVisibility = () => { if (!document.hidden && !inFlight) { if (timer) clearTimeout(timer); void tick(); } };
    document.addEventListener("visibilitychange", onVisibility);
    schedule(2_000);
    return () => { stopped = true; if (timer) clearTimeout(timer); controller?.abort(); document.removeEventListener("visibilitychange", onVisibility); };
  }, [approvalId, missionId, router, status]);
  return null;
}
