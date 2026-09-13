import Link from "next/link";
import { PageHeader } from "@/components/page-header";
import { MissionComposer } from "@/components/mission-composer";
import { ComposerSkeleton } from "@/components/page-skeleton";
import { StreamResource } from "@/components/stream-resource";
import { getProjects, requireSession } from "@/lib/api/server";
import { canManage } from "@/lib/api/types";

export default function NewMissionPage() {
  return <main className="mx-auto max-w-[1440px] px-4 py-6 sm:px-6 lg:px-8">
    <Link href="/missions" className="mb-5 inline-block text-sm text-primary hover:underline">Back to missions</Link>
    <PageHeader eyebrow="Mission intake" title="Create a mission" description="Describe the outcome you need and select the project it belongs to." />
    <div className="grid items-start gap-6 lg:grid-cols-[minmax(0,2fr)_minmax(260px,1fr)]">
      <StreamResource promise={Promise.all([getProjects(), requireSession()])} label="Mission composer" fallback={<ComposerSkeleton />}>{([projects, session]) => canManage(session.current_workspace.role) ? <MissionComposer projects={projects} autoFocus /> : <p className="rounded-xl border bg-card p-5 text-sm text-muted-foreground">Your role can inspect missions. Ask a workspace manager to submit this work.</p>}</StreamResource>
      <aside className="rounded-xl border bg-card p-5"><h2 className="font-semibold">What happens next</h2><ol className="mt-4 space-y-5 text-sm">{[["Context", "Parallax collects relevant evidence from your connected tools."], ["Assessment", "The agent evaluates the work and prepares proposed actions."], ["Approval", "A reviewer approves writes to Jira, Notion, or Slack. GitHub remains read-only."], ["Verification", "Follow execution and read-back results in the mission timeline."]].map(([title, copy], index) => <li key={title} className="flex gap-3"><span className="font-mono text-xs text-primary">{String(index + 1).padStart(2, "0")}</span><div><h3 className="font-medium">{title}</h3><p className="mt-1 leading-6 text-muted-foreground">{copy}</p></div></li>)}</ol></aside>
    </div>
  </main>;
}
