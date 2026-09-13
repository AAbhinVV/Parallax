import { checkIntegrationAction } from "@/app/actions/workspace";
import { MutationForm } from "@/components/mutation-form";
import { PageHeader } from "@/components/page-header";
import { StreamResource } from "@/components/stream-resource";
import { getIntegrationCapabilities, getIntegrationHealth, getIntegrations, requireSession } from "@/lib/api/server";
import { canManage, type IntegrationProvider } from "@/lib/api/types";
import { GitBranch, Ticket, BookOpen, Hash } from "lucide-react";

const providers: IntegrationProvider[] = ["github", "jira", "notion", "slack"];
const icons = { github: GitBranch, jira: Ticket, notion: BookOpen, slack: Hash };

export default function IntegrationsPage() {
  const connections = getIntegrations();
  const health = getIntegrationHealth();
  const session = requireSession();
  return <main className="mx-auto max-w-[1440px] px-4 py-6 sm:px-6 lg:px-8">
    <PageHeader eyebrow="Connected systems" title="Integrations" description="Inspect connections, provider capabilities, and approval requirements." />
    <div className="mb-5 rounded-xl border bg-accent/40 px-4 py-3 text-sm text-muted-foreground">GitHub is read-only. Jira, Notion, and Slack writes require stored approval.</div>
    <div className="grid items-start gap-5 lg:grid-cols-2">{providers.map((provider) => {
      const Icon = icons[provider];
      return <article key={provider} className="overflow-hidden rounded-xl border bg-card">
        <header className="flex items-center gap-3 border-b p-5"><span className="grid size-10 place-items-center rounded-lg bg-muted"><Icon className="size-5" /></span><div><h2 className="font-semibold capitalize">{provider}</h2><p className="mt-1 text-xs text-muted-foreground">{provider === "github" ? "Context and evidence · Read only" : "Context and approved actions"}</p></div></header>
        <div className="space-y-4 p-5">
          <StreamResource promise={connections} label="Connection">{(items) => { const item = items.find((entry) => entry.name.toLowerCase() === provider); return <div><span className={item?.connected ? "rounded-md bg-success-soft px-2 py-1 text-xs text-success" : "rounded-md bg-muted px-2 py-1 text-xs text-muted-foreground"}>{item ? item.connected ? "Connected" : "Disconnected" : "Unknown"}</span><p className="mt-3 text-sm text-muted-foreground">{item?.detail ?? "No connection detail is available."}</p></div>; }}</StreamResource>
          <StreamResource promise={health} label="Stored health">{(items) => { const state = items.find((entry) => entry.name.toLowerCase() === provider); return <div className="flex flex-wrap gap-2 rounded-lg bg-muted p-3 text-xs text-muted-foreground"><span className="capitalize">{state?.status ?? "Unknown health"}</span><span>{state?.mode ?? "Unknown"} mode</span>{state?.last_checked_at && <time dateTime={state.last_checked_at}>Checked {new Date(state.last_checked_at).toLocaleString()}</time>}</div>; }}</StreamResource>
          <StreamResource promise={getIntegrationCapabilities(provider)} label="Capabilities">{(capability) => <ul className="divide-y border-y">{capability.capabilities.map((item) => <li key={item.operation} className="py-3"><div className="flex justify-between gap-3 text-sm"><span className="font-medium">{item.operation}</span><span className="capitalize text-muted-foreground">{item.access}</span></div><p className="mt-1 text-xs leading-5 text-muted-foreground">{item.description}</p></li>)}</ul>}</StreamResource>
          <StreamResource promise={session} label="Connection controls">{(identity) => canManage(identity.current_workspace.role) ? <MutationForm action={checkIntegrationAction.bind(null, provider)} label="Run connection check" variant="outline" /> : <p className="text-xs text-muted-foreground">Your role can inspect connections. A manager can run connection checks.</p>}</StreamResource>
        </div>
      </article>;
    })}</div>
  </main>;
}
