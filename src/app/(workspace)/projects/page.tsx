import { Suspense } from "react";
import Link from "next/link";
import { Activity, ArrowRight, FolderKanban, ShieldCheck } from "lucide-react";
import { PanelSkeleton, KpiSkeleton } from "@/components/page-skeleton";
import { PageHeader } from "@/components/page-header";
import { Button } from "@/components/ui/button";
import { getProjects } from "@/lib/api/server";

async function ProjectsPageContent({ searchParams }: { searchParams: Promise<{ project?: string }> }) {
  const [projects, query] = await Promise.all([getProjects(), searchParams]);
  const selected = projects.find((project) => project.id === query.project) ?? projects[0];
  const averageHealth = projects.length ? Math.round(projects.reduce((sum, project) => sum + project.health_pct, 0) / projects.length) : 0;
  const onTrack = projects.filter((project) => project.health_pct >= 70).length;
  return <main className="mx-auto max-w-[1440px] px-4 pb-8 sm:px-6 lg:px-8">
    <div className="grid gap-3 sm:grid-cols-3">{[{ label: "Projects", value: projects.length, icon: FolderKanban }, { label: "Average health", value: `${averageHealth}%`, icon: Activity }, { label: "On track", value: onTrack, icon: ShieldCheck }].map(({ label, value, icon: Icon }) => <div key={label} className="rounded-xl border bg-card p-4 shadow-xs"><div className="flex items-center justify-between"><span className="text-xs text-muted-foreground">{label}</span><Icon className="size-4 text-primary" /></div><p className="mt-3 font-mono text-2xl font-semibold">{value}</p></div>)}</div>
    <div className="mt-5 grid gap-5 lg:grid-cols-[minmax(0,1.45fr)_minmax(300px,.55fr)]">
      <section className="overflow-hidden rounded-xl border bg-card"><div className="border-b bg-surface-inset px-5 py-4"><h2 className="font-semibold">Project portfolio</h2><p className="mt-1 text-xs text-muted-foreground">Backend-calculated health across the connected workspace.</p></div><div className="divide-y">{projects.map((project) => <Link key={project.id} href={`/projects?project=${project.id}`} className={`grid grid-cols-[minmax(0,1fr)_110px_36px] items-center gap-4 px-5 py-4 transition-colors hover:bg-surface-inset ${selected?.id === project.id ? "bg-primary-subtle" : ""}`}><div className="min-w-0"><p className="truncate text-sm font-medium">{project.name}</p><code className="mt-1 block truncate text-[11px] text-muted-foreground">{project.id}</code></div><div><div className="flex justify-between text-[11px]"><span>Health</span><span className="font-mono">{project.health_pct}%</span></div><div className="mt-1.5 h-1.5 overflow-hidden rounded-full bg-muted"><div className="h-full rounded-full bg-primary" style={{ width: `${Math.max(0, Math.min(100, project.health_pct))}%` }} /></div></div><ArrowRight className="size-4 text-muted-foreground" /></Link>)}{!projects.length && <div className="grid min-h-48 place-items-center text-sm text-muted-foreground">No projects are available.</div>}</div></section>
      <aside className="rounded-xl border bg-card p-5"><p className="text-[11px] font-semibold uppercase tracking-[0.08em] text-muted-foreground">Project inspector</p>{selected ? <><div className="mt-5 flex size-11 items-center justify-center rounded-xl border bg-primary-subtle text-lg" aria-hidden="true">{selected.icon}</div><h2 className="mt-4 text-lg font-semibold">{selected.name}</h2><p className="mt-1 text-sm text-muted-foreground">Current backend health snapshot</p><div className="mt-6 rounded-xl border bg-surface-inset p-4"><div className="flex items-end justify-between"><span className="text-sm">Health score</span><strong className="font-mono text-2xl">{selected.health_pct}%</strong></div><div className="mt-3 h-2 overflow-hidden rounded-full bg-muted"><div className="h-full rounded-full bg-primary" style={{ width: `${Math.max(0, Math.min(100, selected.health_pct))}%` }} /></div></div><dl className="mt-5 space-y-3 text-sm"><div><dt className="text-xs text-muted-foreground">Project identifier</dt><dd className="mt-1 break-all font-mono text-xs">{selected.id}</dd></div></dl><Button className="mt-6 w-full" nativeButton={false} render={<Link href={`/missions?project=${encodeURIComponent(selected.name)}`} />}>View missions</Button></> : <p className="mt-5 text-sm text-muted-foreground">Select a project to inspect it.</p>}</aside>
    </div>
  </main>;
}

export default function ProjectsPage(props: { searchParams: Promise<{ project?: string }> }) {
  return <><div className="mx-auto max-w-[1440px] px-4 pt-6 sm:px-6 lg:px-8"><PageHeader eyebrow="Portfolio intelligence" title="Projects" description="Inspect health snapshots calculated by the Parallax backend." /></div><Suspense fallback={<div className="mx-auto max-w-[1440px] space-y-5 px-4 pb-8 sm:px-6 lg:px-8"><KpiSkeleton count={3} /><PanelSkeleton rows={5} /></div>}><ProjectsPageContent {...props} /></Suspense></>;
}
