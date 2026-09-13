import { Skeleton } from "@/components/ui/skeleton";

export function RowsSkeleton({ rows = 5 }: { rows?: number }) {
  return <div aria-hidden="true" className="divide-y">{Array.from({ length: rows }, (_, i) => <div key={i} className="flex min-h-[76px] items-center gap-3 py-3">
    <Skeleton className="size-9 shrink-0 rounded-lg" />
    <div className="flex-1 space-y-2"><Skeleton className={i % 2 ? "h-4 w-2/3" : "h-4 w-3/4"} /><div className="flex gap-2"><Skeleton className="h-3 w-20" /><Skeleton className="h-3 w-16" /></div></div>
    <Skeleton className="hidden h-5 w-20 sm:block" /><Skeleton className="size-4 shrink-0" />
  </div>)}</div>;
}

export function PanelSkeleton({ rows = 3 }: { rows?: number }) {
  return <section aria-busy="true" aria-label="Loading panel" className="rounded-xl border bg-card p-5"><Skeleton className="mb-3 h-4 w-32" /><RowsSkeleton rows={rows} /></section>;
}

export function KpiSkeleton({ count = 4 }: { count?: number }) {
  const layout = count === 5 ? "grid gap-3 sm:grid-cols-2 xl:grid-cols-5" : count === 3 ? "grid gap-3 sm:grid-cols-3" : "grid gap-3 sm:grid-cols-2 lg:grid-cols-4";
  return <div aria-busy="true" aria-label="Loading metrics" className={layout}>{Array.from({ length: count }, (_, i) => <div key={i} className="flex min-h-24 items-center gap-3 rounded-xl border bg-card p-4"><Skeleton className="size-9 shrink-0 rounded-lg" /><div className="flex-1 space-y-2"><Skeleton className="h-6 w-14" /><Skeleton className="h-3 w-24 max-w-full" /></div></div>)}</div>;
}

export function ComposerSkeleton() {
  return <section aria-busy="true" aria-label="Loading mission composer" className="space-y-5 rounded-lg border bg-card p-5"><div className="flex items-center gap-3"><Skeleton className="size-8" /><Skeleton className="h-4 w-64 max-w-full" /></div><Skeleton className="h-4 w-4/5" /><div className="flex flex-wrap gap-2"><Skeleton className="h-8 w-28" /><Skeleton className="h-8 w-24" /><Skeleton className="h-8 w-28" /></div><div className="flex items-center justify-between border-t pt-4"><Skeleton className="h-9 w-40" /><Skeleton className="h-9 w-28" /></div></section>;
}

export function PageSkeleton({ variant = "cards" }: { variant?: "cards" | "table" | "detail" | "dashboard" }) {
  return <div role="status" aria-label="Loading page" aria-busy="true" className="mx-auto w-full max-w-[1440px] space-y-5 px-4 py-6 sm:px-6 lg:px-8">
    <span className="sr-only">Loading workspace content</span>
    <div className="space-y-2"><Skeleton className="h-3 w-28" /><Skeleton className="h-7 w-64 max-w-full" /><Skeleton className="h-4 w-96 max-w-full" /></div>
    {variant === "dashboard" ? <><KpiSkeleton count={5} /><ComposerSkeleton /><div className="grid gap-5 xl:grid-cols-[2fr_1fr]"><PanelSkeleton rows={6} /><PanelSkeleton rows={4} /></div><div className="grid gap-5 lg:grid-cols-3"><PanelSkeleton /><PanelSkeleton /><PanelSkeleton /></div></>
      : variant === "detail" ? <><KpiSkeleton /><div className="grid gap-5 xl:grid-cols-[1.5fr_1fr]"><div className="space-y-5"><PanelSkeleton rows={6} /><PanelSkeleton rows={4} /></div><div className="space-y-5"><PanelSkeleton rows={2} /><PanelSkeleton rows={3} /><PanelSkeleton rows={3} /></div></div></>
      : variant === "table" ? <><div className="flex flex-wrap gap-3"><Skeleton className="h-10 w-64" /><Skeleton className="h-10 w-32" /><Skeleton className="h-10 w-24" /></div><PanelSkeleton rows={8} /></>
      : <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">{Array.from({ length: 6 }, (_, i) => <PanelSkeleton key={i} rows={2} />)}</div>}
  </div>;
}

export function ShellSkeleton() {
  return <div role="status" aria-label="Loading workspace" className="min-h-dvh lg:grid lg:grid-cols-[232px_minmax(0,1fr)]"><aside className="hidden space-y-6 border-r bg-sidebar p-5 lg:block"><Skeleton className="h-10 w-36" />{Array.from({ length: 8 }, (_, i) => <Skeleton key={i} className="h-9 w-full" />)}<Skeleton className="mt-20 h-16 w-full" /></aside><div><div className="flex h-16 items-center justify-between border-b bg-card px-6"><Skeleton className="h-9 w-64" /><Skeleton className="h-9 w-28" /></div><PageSkeleton variant="dashboard" /></div></div>;
}
