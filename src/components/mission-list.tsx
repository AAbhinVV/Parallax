import Link from "next/link";
import { ArrowRight } from "lucide-react";

import { MissionStatusBadge, formatRelativeTime } from "@/components/mission-status";
import { Button } from "@/components/ui/button";
import { RowsSkeleton } from "@/components/page-skeleton";
import type { Mission, MissionStatus } from "@/lib/api/types";

export function MissionListSkeleton({ rows = 5 }: { rows?: number }) {
  return <RowsSkeleton rows={rows} />;
}

export function MissionList({ missions, limit, filter = "all" }: { missions: Mission[]; limit?: number; filter?: MissionStatus | "all" }) {
  const filtered = missions.filter((mission) => filter === "all" || mission.status === filter).slice(0, limit);
  if (!filtered.length) return <div className="grid min-h-48 place-items-center rounded-xl border border-dashed bg-surface-inset px-6 text-center text-sm text-muted-foreground">No missions match this view.</div>;

  return <div className="overflow-hidden rounded-xl border bg-card">
    <div className="hidden grid-cols-[minmax(280px,1.7fr)_minmax(120px,.7fr)_150px_150px_110px_40px] gap-4 border-b bg-surface-inset px-4 py-2.5 text-[11px] font-semibold uppercase tracking-[0.08em] text-muted-foreground lg:grid"><span>Mission</span><span>Project</span><span>Status</span><span>Progress</span><span>Updated</span><span /></div>
    <div className="divide-y">{filtered.map((mission) => {
      const progress = mission.progress_total > 0 ? Math.min(100, Math.round((mission.progress_current / mission.progress_total) * 100)) : 0;
      return <article key={mission.id} className="group grid min-w-0 grid-cols-[minmax(0,1fr)_auto] items-center gap-3 px-4 py-4 transition-colors hover:bg-surface-inset lg:grid-cols-[minmax(280px,1.7fr)_minmax(120px,.7fr)_150px_150px_110px_40px] lg:gap-4">
        <div className="min-w-0"><Link href={`/missions/${mission.id}`} className="block truncate text-sm font-medium text-foreground hover:text-primary">{mission.prompt}</Link><code className="mt-1 block truncate text-[11px] text-muted-foreground">{mission.id}</code><div className="mt-2 flex flex-wrap items-center gap-2 lg:hidden"><MissionStatusBadge status={mission.status} /><span className="text-xs text-muted-foreground">{mission.project} · {mission.progress_current}/{mission.progress_total} steps</span></div></div>
        <span className="hidden truncate text-sm text-muted-foreground lg:block">{mission.project}</span>
        <div className="hidden lg:block"><MissionStatusBadge status={mission.status} /></div>
        <div className="hidden lg:block"><div className="flex items-center justify-between gap-2 text-[11px] text-muted-foreground"><span>{mission.progress_current}/{mission.progress_total}</span><span>{progress}%</span></div><div className="mt-1.5 h-1.5 overflow-hidden rounded-full bg-muted"><div className="h-full rounded-full bg-primary" style={{ width: `${progress}%` }} /></div></div>
        <time className="hidden text-xs text-muted-foreground lg:block" dateTime={mission.updated_at}>{formatRelativeTime(mission.updated_at)}</time>
        <Button nativeButton={false} variant="ghost" size="icon" render={<Link href={`/missions/${mission.id}`} aria-label={`Open mission ${mission.id}`} />}><ArrowRight className="size-4" /></Button>
      </article>;
    })}</div>
  </div>;
}
