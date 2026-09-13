import { Suspense, type ReactNode } from "react";
import { ApiError } from "@/lib/api/errors";
import { PanelSkeleton } from "@/components/page-skeleton";

async function ResolvedResource<T>({ promise, label, children }: { promise: Promise<T>; label: string; children: (value: T) => ReactNode }) {
  let value: T;
  try { value = await promise; }
  catch (error) {
    if (!(error instanceof ApiError)) throw error;
    return <section role="status" className="rounded-xl border border-dashed bg-card p-5"><h2 className="font-semibold">{label}</h2><p className="mt-2 text-sm text-muted-foreground">{error.status === 404 ? "Not available yet." : error.status === 403 ? "Your role does not have access to this information." : "This information could not be loaded. Refresh to try again."}</p>{error.correlationId && <p className="mt-2 break-all font-mono text-xs text-muted-foreground">Reference {error.correlationId}</p>}</section>;
  }
  return children(value);
}

/** Server-only rendering boundary: each upstream resource streams independently. */
export function StreamResource<T>({ promise, label, children, fallback }: { promise: Promise<T>; label: string; children: (value: T) => ReactNode; fallback?: ReactNode }) {
  return <Suspense fallback={fallback ?? <PanelSkeleton />}><ResolvedResource promise={promise} label={label}>{children}</ResolvedResource></Suspense>;
}
