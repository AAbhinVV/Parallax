"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

import { terminalMissionStatuses, type MissionStatus } from "@/lib/api/types";
import { pollingDelay } from "@/lib/pagination";

type LiveDashboard = { data?: { missions?: Array<{ status?: MissionStatus }> } };

export function DashboardPoller({ active }: { active: boolean }) {
  const router = useRouter();
  useEffect(() => {
    if (!active) return;
    let timer: ReturnType<typeof setTimeout> | undefined;
    let controller: AbortController | undefined;
    let failures = 0;
    let stopped = false;
    let inFlight = false;

    const schedule = (delay: number) => { if (!stopped) timer = setTimeout(tick, delay); };
    const tick = async () => {
      if (stopped || inFlight) return;
      if (document.hidden) { schedule(5_000); return; }
      inFlight = true;
      controller = new AbortController();
      try {
        const response = await fetch("/api/ui/dashboard/live", { cache: "no-store", signal: controller.signal });
        if (response.status === 401) { stopped = true; router.replace("/login"); return; }
        if (!response.ok) throw new Error("Dashboard refresh failed");
        const payload = await response.json() as LiveDashboard;
        failures = 0;
        const missions = payload.data?.missions;
        if (missions && !missions.some((mission) => mission.status && !terminalMissionStatuses.has(mission.status))) stopped = true;
        router.refresh();
      } catch (error) { if ((error as Error).name !== "AbortError") failures += 1; }
      finally { inFlight = false; }
      schedule(pollingDelay(failures, 5_000));
    };
    const onVisibility = () => { if (!document.hidden && !inFlight) { if (timer) clearTimeout(timer); void tick(); } };
    document.addEventListener("visibilitychange", onVisibility);
    schedule(5_000);
    return () => { stopped = true; if (timer) clearTimeout(timer); controller?.abort(); document.removeEventListener("visibilitychange", onVisibility); };
  }, [active, router]);
  return null;
}
