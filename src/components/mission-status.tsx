import { AlertTriangle, Ban, CheckCircle2, CircleDashed, Clock3, LoaderCircle, ShieldQuestion, XCircle } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { normalizeDate, type MissionStatus } from "@/lib/api/types";
import { cn } from "@/lib/utils";

const statusConfig: Record<MissionStatus, { label: string; className: string; icon: typeof Clock3 }> = {
  queued: { label: "Queued", className: "border-border bg-muted text-muted-foreground", icon: Clock3 },
  planning: { label: "Planning", className: "border-info/25 bg-info-soft text-foreground", icon: CircleDashed },
  context_collected: { label: "Context collected", className: "border-info/25 bg-info-soft text-foreground", icon: CheckCircle2 },
  waiting_for_approval: { label: "Awaiting approval", className: "border-warning/30 bg-warning-soft text-foreground", icon: ShieldQuestion },
  running: { label: "Running", className: "border-info/25 bg-info-soft text-foreground", icon: LoaderCircle },
  waiting_for_event: { label: "Waiting for event", className: "border-warning/30 bg-warning-soft text-foreground", icon: Clock3 },
  completed: { label: "Completed", className: "border-success/25 bg-success-soft text-foreground", icon: CheckCircle2 },
  blocked: { label: "Blocked", className: "border-warning/30 bg-warning-soft text-foreground", icon: AlertTriangle },
  rejected: { label: "Rejected", className: "border-destructive/25 bg-danger-soft text-destructive", icon: Ban },
  cancelled: { label: "Cancelled", className: "border-border bg-muted text-muted-foreground", icon: Ban },
  partially_complete: { label: "Partially complete", className: "border-warning/30 bg-warning-soft text-foreground", icon: AlertTriangle },
  failed: { label: "Failed", className: "border-destructive/25 bg-danger-soft text-destructive", icon: XCircle },
};

export function MissionStatusBadge({ status }: { status: MissionStatus }) {
  const config = statusConfig[status] ?? { label: String(status).replaceAll("_", " "), className: "border-border bg-muted text-muted-foreground", icon: CircleDashed };
  const Icon = config.icon;
  return <Badge variant="outline" className={cn("gap-1.5", config.className)}><Icon className={cn("size-3.5", status === "running" && "motion-safe:animate-spin")} aria-hidden="true" />{config.label}</Badge>;
}

export function formatRelativeTime(value: string) {
  const minutes = Math.max(0, Math.round((Date.now() - Date.parse(normalizeDate(value))) / 60_000));
  if (minutes < 1) return "just now";
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.round(hours / 24)}d ago`;
}
