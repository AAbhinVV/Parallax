import { Suspense } from "react";
import { Activity, CheckCircle2, Clock3, Gauge, ShieldCheck } from "lucide-react";
import { PanelSkeleton, KpiSkeleton } from "@/components/page-skeleton";
import { PageHeader } from "@/components/page-header";
import { getAnalytics } from "@/lib/api/server";

async function AnalyticsPageContent() {
  const data = await getAnalytics();
  const executionTotal = data.executions_by_provider.reduce((sum, item) => sum + item.verified + item.failed, 0);
  const metrics = [{ label: "Total missions", value: data.total_missions, icon: Activity }, { label: "Completion rate", value: `${data.completion_rate_pct}%`, icon: CheckCircle2 }, { label: "Verification rate", value: `${data.verification_rate_pct}%`, icon: ShieldCheck }, { label: "Average completion", value: data.average_completion_seconds == null ? "—" : `${Math.round(data.average_completion_seconds)}s`, icon: Clock3 }, { label: "Provider executions", value: executionTotal, icon: Gauge }];
  return <main className="mx-auto max-w-[1440px] px-4 pb-8 sm:px-6 lg:px-8">
    <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5">{metrics.map(({ label, value, icon: Icon }) => <div key={label} className="rounded-xl border bg-card p-4 shadow-xs"><div className="flex items-center justify-between"><span className="text-xs text-muted-foreground">{label}</span><Icon className="size-4 text-primary" /></div><p className="mt-3 font-mono text-2xl font-semibold">{value}</p></div>)}</div>
    <div className="mt-5 grid gap-5 xl:grid-cols-[minmax(0,1.1fr)_minmax(340px,.9fr)]">
      <section className="rounded-xl border bg-card p-5"><h2 className="font-semibold">Mission distribution</h2><p className="mt-1 text-xs text-muted-foreground">Every lifecycle state reported by the API.</p><div className="mt-6 space-y-4">{data.missions_by_status.map((item) => { const width = data.total_missions ? Math.min(100, item.count / data.total_missions * 100) : 0; return <div key={item.status} className="grid grid-cols-[150px_minmax(0,1fr)_40px] items-center gap-3 text-sm"><span className="truncate capitalize">{item.status.replaceAll("_", " ")}</span><div className="h-2 overflow-hidden rounded-full bg-muted"><div className="h-full rounded-full bg-primary" style={{ width: `${width}%` }} /></div><span className="text-right font-mono text-xs">{item.count}</span></div>; })}{!data.missions_by_status.length && <p className="text-sm text-muted-foreground">No mission analytics are available yet.</p>}</div></section>
      <section className="overflow-hidden rounded-xl border bg-card"><div className="border-b bg-surface-inset px-5 py-4"><h2 className="font-semibold">Execution verification</h2><p className="mt-1 text-xs text-muted-foreground">Read-back outcomes grouped by provider.</p></div><div className="grid grid-cols-[1fr_90px_90px] border-b px-5 py-2.5 text-[11px] font-semibold uppercase tracking-[0.08em] text-muted-foreground"><span>Provider</span><span>Verified</span><span>Failed</span></div><div className="divide-y">{data.executions_by_provider.map((item) => <div key={item.provider} className="grid grid-cols-[1fr_90px_90px] items-center px-5 py-4 text-sm"><span className="font-medium capitalize">{item.provider}</span><span className="font-mono text-success">{item.verified}</span><span className="font-mono text-destructive">{item.failed}</span></div>)}{!data.executions_by_provider.length && <p className="p-5 text-sm text-muted-foreground">No provider executions are available yet.</p>}</div></section>
    </div>
  </main>;
}

export default function AnalyticsPage() {
  return <><div className="mx-auto max-w-[1440px] px-4 pt-6 sm:px-6 lg:px-8"><PageHeader eyebrow="Measured outcomes" title="Analytics" description="Mission completion, verification, duration, status, and provider results." /></div><Suspense fallback={<div className="mx-auto max-w-[1440px] space-y-5 px-4 pb-8 sm:px-6 lg:px-8"><KpiSkeleton count={5} /><PanelSkeleton rows={5} /></div>}><AnalyticsPageContent /></Suspense></>;
}
