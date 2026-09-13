import { Suspense } from "react";
import Link from "next/link";
import { Crown, ShieldCheck, Users } from "lucide-react";
import { updateRoleAction } from "@/app/actions/workspace";
import { MutationForm } from "@/components/mutation-form";
import { KpiSkeleton, PanelSkeleton } from "@/components/page-skeleton";
import { PageHeader } from "@/components/page-header";
import { getMembers, requireSession } from "@/lib/api/server";
import { canManage, type WorkspaceRole } from "@/lib/api/types";

const roles: WorkspaceRole[] = ["owner", "admin", "manager", "reviewer", "viewer"];

async function TeamPageContent({ searchParams }: { searchParams: Promise<{ member?: string }> }) {
  const [members, session, query] = await Promise.all([getMembers(), requireSession(), searchParams]);
  const manager = canManage(session.current_workspace.role);
  const selected = members.find((member) => member.user_id === query.member) ?? members[0];
  const leadership = members.filter((member) => ["owner", "admin", "manager"].includes(member.role)).length;
  const metrics = [
    { label: "Workspace members", value: members.length, icon: Users },
    { label: "Leadership roles", value: leadership, icon: Crown },
    { label: "Your access", value: session.current_workspace.role, icon: ShieldCheck },
  ];

  return <main className="mx-auto max-w-[1440px] px-4 pb-8 sm:px-6 lg:px-8">
    <div className="grid gap-3 sm:grid-cols-3">{metrics.map(({ label, value, icon: Icon }) => <div key={label} className="rounded-xl border bg-card p-4 shadow-xs"><div className="flex items-center justify-between"><span className="text-xs text-muted-foreground">{label}</span><Icon className="size-4 text-primary" /></div><p className="mt-3 truncate font-mono text-xl font-semibold capitalize">{value}</p></div>)}</div>
    <div className="mt-5 grid gap-5 lg:grid-cols-[minmax(0,1.5fr)_minmax(300px,.5fr)]">
      <section className="overflow-hidden rounded-xl border bg-card">
        <div className="grid grid-cols-[minmax(220px,1fr)_130px_90px] border-b bg-surface-inset px-5 py-2.5 text-[11px] font-semibold uppercase tracking-[0.08em] text-muted-foreground"><span>Member</span><span>Role</span><span>Access</span></div>
        <div className="divide-y">{members.map((member) => <Link key={member.user_id} href={`/team?member=${member.user_id}`} className={`grid grid-cols-[minmax(220px,1fr)_130px_90px] items-center px-5 py-4 text-sm hover:bg-surface-inset ${selected?.user_id === member.user_id ? "bg-primary-subtle" : ""}`}><div className="min-w-0"><p className="truncate font-medium">{member.display_name}</p><p className="truncate text-xs text-muted-foreground">{member.email}</p></div><span className="capitalize">{member.role}</span><span className="text-xs text-muted-foreground">{["owner", "admin", "manager"].includes(member.role) ? "Manage" : member.role === "reviewer" ? "Review" : "View"}</span></Link>)}</div>
      </section>
      <aside className="rounded-xl border bg-card p-5">
        <p className="text-[11px] font-semibold uppercase tracking-[0.08em] text-muted-foreground">Member inspector</p>
        {selected ? <><div className="mt-5 flex size-11 items-center justify-center rounded-full bg-primary-subtle font-semibold text-primary">{selected.display_name.slice(0, 2).toUpperCase()}</div><h2 className="mt-4 font-semibold">{selected.display_name}</h2><p className="mt-1 break-all text-xs text-muted-foreground">{selected.email}</p><dl className="mt-5 grid grid-cols-2 gap-3 text-sm"><div className="rounded-lg border bg-surface-inset p-3"><dt className="text-xs text-muted-foreground">Current role</dt><dd className="mt-1 font-medium capitalize">{selected.role}</dd></div><div className="rounded-lg border bg-surface-inset p-3"><dt className="text-xs text-muted-foreground">Status</dt><dd className="mt-1 font-medium text-success">Active</dd></div></dl>{manager ? <MutationForm action={updateRoleAction.bind(null, selected.user_id)} label="Update role" className="mt-5"><label className="mb-2 block text-xs font-medium" htmlFor="member-role">Workspace role</label><select id="member-role" name="role" defaultValue={selected.role} className="mb-3 min-h-10 w-full rounded-lg border bg-background px-3 text-sm">{roles.map((role) => <option key={role}>{role}</option>)}</select></MutationForm> : <p className="mt-5 rounded-lg border bg-surface-inset p-3 text-xs text-muted-foreground">Your role has read-only access to membership settings.</p>}</> : <p className="mt-5 text-sm text-muted-foreground">No members are available.</p>}
      </aside>
    </div>
  </main>;
}

export default function TeamPage(props: { searchParams: Promise<{ member?: string }> }) {
  return <><div className="mx-auto max-w-[1440px] px-4 pt-6 sm:px-6 lg:px-8"><PageHeader eyebrow="Workspace governance" title="Team" description="Inspect membership, access level, and role assignments." /></div><Suspense fallback={<div className="mx-auto max-w-[1440px] space-y-5 px-4 pb-8 sm:px-6 lg:px-8"><KpiSkeleton /><PanelSkeleton rows={8} /></div>}><TeamPageContent {...props} /></Suspense></>;
}
