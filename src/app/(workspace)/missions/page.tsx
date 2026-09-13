import { Suspense } from "react";
import Link from "next/link";
import { AlertTriangle, CheckCircle2, CircleDot, Clock3, Plus } from "lucide-react";

import { MissionList } from "@/components/mission-list";
import { PanelSkeleton, KpiSkeleton } from "@/components/page-skeleton";
import { PageHeader } from "@/components/page-header";
import { Button } from "@/components/ui/button";
import { getMissions } from "@/lib/api/server";
import type { MissionStatus } from "@/lib/api/types";

const statuses: Array<MissionStatus | "all"> = ["all", "queued", "planning", "context_collected", "waiting_for_approval", "running", "completed", "blocked", "rejected", "cancelled", "partially_complete", "failed"];
const pageSize = 20;

async function MissionsPageContent({ searchParams }: { searchParams: Promise<{ page?: string; status?: string; project?: string }> }) {
  const query = await searchParams;
  const page = Math.max(1, Number.parseInt(query.page ?? "1", 10) || 1);
  const status = statuses.includes(query.status as MissionStatus) ? query.status as MissionStatus : "all";
  const pageMissions = await getMissions(pageSize, (page - 1) * pageSize);
  const missions = query.project ? pageMissions.filter((mission) => mission.project === query.project) : pageMissions;
  const counts = {
    active: missions.filter((mission) => !["completed", "rejected", "cancelled", "failed"].includes(mission.status)).length,
    approval: missions.filter((mission) => mission.status === "waiting_for_approval").length,
    blocked: missions.filter((mission) => ["blocked", "failed"].includes(mission.status)).length,
    completed: missions.filter((mission) => mission.status === "completed").length,
  };
  const href = (nextPage: number) => `/missions?page=${nextPage}${status === "all" ? "" : `&status=${status}`}${query.project ? `&project=${encodeURIComponent(query.project)}` : ""}`;
  const metrics = [
    { label: "Active on this page", value: counts.active, icon: CircleDot },
    { label: "Awaiting approval", value: counts.approval, icon: Clock3 },
    { label: "Needs attention", value: counts.blocked, icon: AlertTriangle },
    { label: "Completed", value: counts.completed, icon: CheckCircle2 },
  ];

  return <main className="mx-auto max-w-[1440px] px-4 pb-8 sm:px-6 lg:px-8">
    <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">{metrics.map(({ label, value, icon: Icon }) => <div key={label} className="rounded-xl border bg-card p-4 shadow-xs"><div className="flex items-center justify-between"><p className="text-xs text-muted-foreground">{label}</p><Icon className="size-4 text-primary" /></div><p className="mt-3 font-mono text-2xl font-semibold">{value}</p></div>)}</div>
    <section className="mt-5"><div className="mb-3 flex flex-wrap items-end justify-between gap-3"><div><h2 className="font-semibold">Mission archive</h2><p className="text-xs text-muted-foreground">Showing {missions.length} records from the current backend page{query.project ? ` for ${query.project}` : ""}.</p></div>{query.project && <Button nativeButton={false} size="sm" variant="outline" render={<Link href="/missions" />}>Clear project filter</Button>}</div>
      <nav className="mb-4 flex gap-2 overflow-x-auto pb-1" aria-label="Mission status filters">{statuses.map((item) => { const params = new URLSearchParams(); if (item !== "all") params.set("status", item); if (query.project) params.set("project", query.project); return <Button key={item} nativeButton={false} size="sm" variant={item === status ? "default" : "outline"} render={<Link href={`/missions${params.size ? `?${params}` : ""}`} />}>{item.replaceAll("_", " ")}</Button>; })}</nav>
      <MissionList missions={missions} filter={status} />
    </section>
    <div className="mt-5 flex justify-between"><Button nativeButton={false} variant="outline" disabled={page === 1} render={page > 1 ? <Link href={href(page - 1)} /> : undefined}>Previous</Button><span className="self-center font-mono text-xs text-muted-foreground">Page {page}</span><Button nativeButton={false} variant="outline" disabled={pageMissions.length < pageSize} render={pageMissions.length === pageSize ? <Link href={href(page + 1)} /> : undefined}>Next</Button></div>
  </main>;
}

export default function MissionsPage(props: { searchParams: Promise<{ page?: string; status?: string; project?: string }> }) {
  return <><div className="mx-auto max-w-[1440px] px-4 pt-6 sm:px-6 lg:px-8"><PageHeader eyebrow="Operations queue" title="Missions" description="Track every mission from intake through verified execution." action={<Button nativeButton={false} render={<Link href="/missions/new" />}><Plus />New mission</Button>} /></div><Suspense fallback={<div className="mx-auto max-w-[1440px] space-y-5 px-4 pb-8 sm:px-6 lg:px-8"><KpiSkeleton /><PanelSkeleton rows={8} /></div>}><MissionsPageContent {...props} /></Suspense></>;
}
