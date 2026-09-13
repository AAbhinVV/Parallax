import Link from "next/link";
import { BookOpenText, ChevronRight, CircleAlert, Cpu, GitBranch, Layers3, MessageSquare, RefreshCw, Smartphone, TicketCheck, WalletCards, Wrench } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import type { ActivityItem, Integration, Mission, Project } from "@/lib/api/types";
import { formatRelativeTime } from "@/components/mission-status";

function Panel({ title, href, children }: { title: string; href?: string; children: React.ReactNode }) {
  return (
    <section className="overflow-hidden rounded-xl border bg-card shadow-xs" aria-labelledby={`panel-${title.toLowerCase().replaceAll(" ", "-")}`}>
      <div className="flex min-h-12 items-center justify-between border-b px-4">
        <h2 id={`panel-${title.toLowerCase().replaceAll(" ", "-")}`} className="text-sm font-semibold">{title}</h2>
        {href && <Button nativeButton={false} variant="ghost" size="sm" render={<Link href={href} />}>View all<ChevronRight className="size-3.5" /></Button>}
      </div>
      <div className="p-4">{children}</div>
    </section>
  );
}

const integrationIcons = { GitHub: GitBranch, Jira: TicketCheck, Notion: BookOpenText, Slack: MessageSquare };

export function ConnectedAppsPanel({ integrations, loading }: { integrations?: Integration[]; loading?: boolean }) {
  return (
    <Panel title="Connected apps" href="/integrations">
      {loading ? <Skeleton className="h-44 w-full" /> : <div className="divide-y">
        {integrations?.map((integration) => {
          const Icon = integrationIcons[integration.name as keyof typeof integrationIcons] ?? Wrench;
          return <div key={integration.name} className="flex items-center gap-3 py-3 first:pt-0 last:pb-0">
            <span className="grid size-9 place-items-center rounded-lg border bg-surface-inset"><Icon className="size-4" aria-hidden="true" /></span>
            <div className="min-w-0 flex-1"><div className="text-sm font-medium">{integration.name}</div><div className="truncate text-xs text-muted-foreground">{integration.detail}</div></div>
            <span className="flex items-center gap-1.5 text-xs"><span className={`size-1.5 rounded-full ${integration.connected ? "bg-success" : "bg-muted-foreground"}`} aria-hidden="true" />{integration.connected ? "Connected" : "Unavailable"}</span>
          </div>;
        })}
      </div>}
    </Panel>
  );
}

const projectIcons = { wallet: WalletCards, layers: Layers3, cpu: Cpu, smartphone: Smartphone };

export function ProjectsPanel({ projects, loading }: { projects?: Project[]; loading?: boolean }) {
  return (
    <Panel title="Project health" href="/projects">
      {loading ? <Skeleton className="h-36 w-full" /> : <div className="space-y-4">
        {projects?.map((project) => {
          const Icon = projectIcons[project.icon as keyof typeof projectIcons] ?? Layers3;
          return <div key={project.name} className="grid grid-cols-[auto_minmax(0,1fr)_auto] items-center gap-3">
            <Icon className="size-4 text-muted-foreground" aria-hidden="true" />
            <div className="min-w-0"><div className="mb-1.5 flex justify-between gap-3 text-sm"><span className="truncate">{project.name}</span><span className="font-mono text-xs text-muted-foreground">{project.health_pct}%</span></div><div className="h-1.5 overflow-hidden rounded-full bg-muted"><div className={`h-full rounded-full ${project.health_pct >= 70 ? "bg-success" : project.health_pct >= 50 ? "bg-warning" : "bg-destructive"}`} style={{ width: `${project.health_pct}%` }} /></div></div>
          </div>;
        })}
      </div>}
    </Panel>
  );
}

function activityIcon(item: ActivityItem) {
  const value = `${item.icon} ${item.title}`.toLowerCase();
  if (value.includes("slack")) return MessageSquare;
  if (value.includes("jira") || value.includes("issue")) return TicketCheck;
  if (value.includes("notion")) return BookOpenText;
  return GitBranch;
}

export function ActivityPanel({ activity, loading }: { activity?: ActivityItem[]; loading?: boolean }) {
  return (
    <Panel title="Recent activity">
      {loading ? <Skeleton className="h-52 w-full" /> : !activity?.length ? <p className="text-sm text-muted-foreground">Activity will appear after the first mission runs.</p> : <ol className="space-y-4">
        {activity.slice(0, 5).map((item) => {
          const Icon = activityIcon(item);
          return <li key={item.id} className="grid grid-cols-[auto_minmax(0,1fr)] gap-3"><span className="grid size-8 place-items-center rounded-full bg-surface-inset"><Icon className="size-3.5" aria-hidden="true" /></span><div className="min-w-0"><div className="truncate text-sm font-medium capitalize">{item.title}</div><p className="line-clamp-2 text-xs leading-5 text-muted-foreground">{item.detail}</p><time className="font-mono text-xs text-muted-foreground" dateTime={item.created_at}>{formatRelativeTime(item.created_at)}</time></div></li>;
        })}
      </ol>}
    </Panel>
  );
}

export function AgentInsightsPanel({ missions }: { missions?: Mission[] }) {
  const failed = missions?.filter((mission) => mission.status === "failed" || mission.status === "blocked") ?? [];
  const queued = missions?.filter((mission) => mission.status === "queued") ?? [];
  return (
    <Panel title="Agent insights">
      <div className="space-y-3">
        {failed.length > 0 && <Link href="/missions?status=failed" className="flex gap-3 rounded-lg border border-destructive/20 bg-danger-soft p-3 hover:border-destructive/40"><CircleAlert className="mt-0.5 size-4 shrink-0 text-destructive" /><span><span className="block text-sm font-medium">{failed.length} mission {failed.length === 1 ? "needs" : "need"} attention</span><span className="mt-1 block text-xs leading-5 text-muted-foreground">Open the failure record to inspect completed steps and the backend error.</span></span></Link>}
        {queued.length > 0 && <div className="flex gap-3 rounded-lg border bg-surface-inset p-3"><RefreshCw className="mt-0.5 size-4 shrink-0 text-info" /><span><span className="block text-sm font-medium">{queued.length} {queued.length === 1 ? "mission is" : "missions are"} queued</span><span className="mt-1 block text-xs leading-5 text-muted-foreground">Queued work is waiting for the agent runner, not human approval.</span></span></div>}
        {!failed.length && !queued.length && <p className="text-sm text-muted-foreground">No blocked or queued work needs attention.</p>}
      </div>
    </Panel>
  );
}

export function QuickActionsPanel() {
  const actions = [
    ["Summarize recent work", "Check recently merged pull requests and summarize what shipped."],
    ["Find open pull requests", "Find open pull requests that still need attention."],
    ["Update Jira from GitHub", "Check merged pull requests and update matching Jira issues to Done."],
    ["Notify the team", "Post a concise project status update in Slack."],
  ];
  return <Panel title="Quick actions"><div className="divide-y">{actions.map(([label, prompt]) => <Link key={label} href={`/dashboard?prompt=${encodeURIComponent(prompt)}&compose=1`} className="flex min-h-11 w-full items-center justify-between gap-3 py-2 text-left text-sm hover:text-primary"><span>{label}</span><ChevronRight className="size-4 shrink-0 text-muted-foreground" /></Link>)}</div></Panel>;
}
