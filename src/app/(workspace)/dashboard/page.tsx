import Link from "next/link";
import { Suspense } from "react";
import { Activity, CheckCheck, CircleAlert, Clock3, ListTodo } from "lucide-react";

import { DashboardPoller } from "@/components/dashboard-poller";
import { ActivityPanel, AgentInsightsPanel, ConnectedAppsPanel, ProjectsPanel, QuickActionsPanel } from "@/components/dashboard-panels";
import { MissionComposer } from "@/components/mission-composer";
import { MissionList, MissionListSkeleton } from "@/components/mission-list";
import { Button } from "@/components/ui/button";
import { PanelSkeleton, KpiSkeleton, ComposerSkeleton } from "@/components/page-skeleton";
import { ApiError } from "@/lib/api/errors";
import { getActivity, getIntegrations, getMissions, getProjects, getStats, requireSession } from "@/lib/api/server";
import { canManage } from "@/lib/api/types";

async function load<T>(promise: Promise<T>): Promise<{ data: T; error?: never } | { data?: never; error: unknown }> {
  try { return { data: await promise }; } catch (error) { return { error }; }
}

function PanelFailure({ label, error }: { label: string; error: unknown }) { return <section className="rounded-xl border border-dashed bg-card p-5 text-sm text-muted-foreground"><span className="font-medium text-foreground">{label}</span> could not be loaded.{error instanceof ApiError && error.correlationId && <span className="mt-1 block font-mono text-xs">Reference {error.correlationId}</span>}</section>; }
function StatsSkeleton() { return <div className="mb-5"><KpiSkeleton count={5} /></div>; }

async function StatsStrip() {
  const result = await load(getStats());
  if ("error" in result) return <div className="mb-5"><PanelFailure label="Mission summary" error={result.error} /></div>;
  const stats = result.data;
  const items = [["Active", stats.active_tasks, Activity], ["Completed · 7d", stats.completed_this_week, CheckCheck], ["Blocked", stats.blocked, CircleAlert], ["Awaiting approval", stats.awaiting_approval, Clock3]] as const;
  return <section aria-label="Mission summary" className="mb-5 grid rounded-xl border bg-card sm:grid-cols-2 xl:grid-cols-[repeat(4,minmax(0,1fr))_1.1fr]">{items.map(([label, value, Icon]) => <div key={label} className="flex min-h-24 items-center gap-3 border-b px-4 sm:border-r xl:border-b-0"><span className="grid size-9 place-items-center rounded-lg bg-surface-inset"><Icon className="size-4" /></span><span><span className="block font-mono text-2xl font-semibold">{value}</span><span className="block text-sm text-muted-foreground">{label}</span></span></div>)}<div className="flex min-h-24 items-center gap-3 px-4 sm:col-span-2 xl:col-span-1"><div className="grid size-12 place-items-center rounded-full border-[5px] border-primary/25 font-mono text-xs font-semibold">{Math.round(stats.project_health_pct)}%</div><div><div className="text-sm font-medium">Project health</div><div className="text-xs text-muted-foreground">Live snapshot</div></div></div></section>;
}

async function Composer({ prompt, autoFocus }: { prompt?: string; autoFocus: boolean }) {
  const result = await load(Promise.all([requireSession(), getProjects()]));
  if ("error" in result) return <PanelFailure label="Mission composer projects" error={result.error} />;
  const [session, projects] = result.data;
  if (!canManage(session.current_workspace.role)) return <section className="rounded-xl border bg-card p-5"><h2 className="text-sm font-semibold">Mission composer</h2><p className="mt-2 text-sm text-muted-foreground">Your workspace role can inspect missions but cannot create them.</p></section>;
  return <MissionComposer projects={projects} suggestedPrompt={prompt} autoFocus={autoFocus} />;
}

async function RecentMissions() {
  const result = await load(getMissions(6, 0));
  if ("error" in result) return <PanelFailure label="Recent missions" error={result.error} />;
  const missions = result.data;
  const active = missions.some((mission) => !["completed", "blocked", "rejected", "cancelled", "partially_complete", "failed"].includes(mission.status));
  return <><section className="min-w-0 rounded-xl border bg-card" aria-labelledby="recent-missions-title"><div className="flex min-h-12 items-center justify-between border-b px-4"><div className="flex items-center gap-2"><ListTodo className="size-4 text-muted-foreground" /><h2 id="recent-missions-title" className="text-sm font-semibold">Recent missions</h2></div><Button nativeButton={false} variant="ghost" size="sm" render={<Link href="/missions" />}>View all</Button></div><div className="px-4 pb-2"><MissionList missions={missions} limit={6} /></div></section><DashboardPoller active={active} /></>;
}

async function ConnectedApps() { const result = await load(getIntegrations()); return "error" in result ? <PanelFailure label="Connected apps" error={result.error} /> : <ConnectedAppsPanel integrations={result.data} />; }
async function RecentActivity() { const result = await load(getActivity(10, 0)); return "error" in result ? <PanelFailure label="Recent activity" error={result.error} /> : <ActivityPanel activity={result.data} />; }
async function Projects() { const result = await load(getProjects()); return "error" in result ? <PanelFailure label="Projects" error={result.error} /> : <ProjectsPanel projects={result.data} />; }
async function Insights() { const result = await load(getMissions(20, 0)); return "error" in result ? <PanelFailure label="Agent insights" error={result.error} /> : <AgentInsightsPanel missions={result.data} />; }

export default async function DashboardPage({ searchParams }: { searchParams: Promise<{ prompt?: string; compose?: string }> }) {
  const [{ prompt, compose }, session] = await Promise.all([searchParams, requireSession()]);
  return <div className="mx-auto w-full max-w-[1440px] px-4 py-6 sm:px-6 lg:px-8 lg:py-8"><header className="mb-6"><p className="mb-1 text-xs font-medium text-muted-foreground">{session.current_workspace.name}</p><h1 className="text-[22px] font-semibold tracking-tight">Good to see you, {session.user.display_name.split(" ")[0]}</h1><p className="mt-1 text-sm text-muted-foreground">Track agent work across connected systems.</p></header><Suspense fallback={<StatsSkeleton />}><StatsStrip /></Suspense><div className="mb-5"><Suspense fallback={<ComposerSkeleton />}><Composer prompt={prompt} autoFocus={compose === "1"} /></Suspense></div><div className="grid min-w-0 gap-5 xl:grid-cols-[minmax(0,2fr)_minmax(290px,0.82fr)]"><Suspense fallback={<div className="rounded-xl border bg-card p-4"><MissionListSkeleton rows={6} /></div>}><RecentMissions /></Suspense><div className="min-w-0 space-y-5"><Suspense fallback={<PanelSkeleton />}><ConnectedApps /></Suspense><Suspense fallback={<PanelSkeleton rows={5} />}><RecentActivity /></Suspense></div></div><div className="mt-5 grid gap-5 lg:grid-cols-3"><Suspense fallback={<PanelSkeleton />}><Projects /></Suspense><Suspense fallback={<PanelSkeleton />}><Insights /></Suspense><QuickActionsPanel /></div></div>;
}
