"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useId, useState } from "react";
import { Activity, Bell, Boxes, BriefcaseBusiness, Cable, ChartNoAxesCombined, Command as CommandIcon, LayoutDashboard, LogOut, Menu, Plus, Search, ScrollText, Settings, Users } from "lucide-react";
import { LayoutGroup, motion, useReducedMotion } from "framer-motion";

import { logoutAction } from "@/app/actions/auth";
import { Button } from "@/components/ui/button";
import { CommandDialog, CommandEmpty, CommandGroup, CommandInput, CommandItem, CommandList, CommandShortcut } from "@/components/ui/command";
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle, SheetTrigger } from "@/components/ui/sheet";
import type { MeResponse, ReadyResponse } from "@/lib/api/types";
import { cn } from "@/lib/utils";

const navigation = [
  { label: "Dashboard", href: "/dashboard", icon: LayoutDashboard },
  { label: "Missions", href: "/missions", icon: BriefcaseBusiness },
  { label: "Projects", href: "/projects", icon: Boxes },
  { label: "Integrations", href: "/integrations", icon: Cable },
  { label: "Activity", href: "/activity", icon: ScrollText },
  { label: "Team", href: "/team", icon: Users },
  { label: "Analytics", href: "/analytics", icon: ChartNoAxesCombined },
  { label: "Settings", href: "/settings", icon: Settings },
];

function Brand() {
  return <Link href="/dashboard" className="flex min-w-0 items-center gap-3 rounded-md focus-visible:outline-offset-4"><span className="grid size-9 shrink-0 place-items-center rounded-lg bg-sidebar-accent font-mono text-sm font-bold text-sidebar-foreground">P</span><span className="min-w-0"><span className="block text-base font-semibold leading-5 text-sidebar-foreground">Parallax</span><span className="block truncate text-xs text-sidebar-muted">Engineering operations</span></span></Link>;
}

function Navigation({ onNavigate }: { onNavigate?: () => void }) {
  const pathname = usePathname();
  const groupId = useId();
  const reduceMotion = useReducedMotion();
  const [hoveredHref, setHoveredHref] = useState<string | null>(null);
  const activeHref = navigation.find(({ href }) => pathname === href || (href !== "/dashboard" && pathname.startsWith(`${href}/`)))?.href;
  const highlightedHref = hoveredHref ?? activeHref;

  return <LayoutGroup id={groupId}><nav aria-label="Primary navigation" className="mt-8 space-y-1" onMouseLeave={() => setHoveredHref(null)}>{navigation.map(({ label, href, icon: Icon }) => {
    const active = activeHref === href;
    const highlighted = highlightedHref === href;
    return <Link key={href} href={href} onClick={onNavigate} onMouseEnter={() => setHoveredHref(href)} onFocus={() => setHoveredHref(href)} onBlur={() => setHoveredHref(null)} aria-current={active ? "page" : undefined} className={cn("relative isolate flex min-h-11 items-center gap-3 rounded-lg px-3 text-sm font-medium text-sidebar-muted outline-none transition-colors duration-200 focus-visible:ring-2 focus-visible:ring-primary/35", highlighted && "text-primary")}>
      {highlighted && <motion.span layoutId="sidebar-highlight" className="absolute inset-0 -z-10 rounded-lg bg-sidebar-accent" initial={false} transition={reduceMotion ? { duration: 0 } : { type: "spring", stiffness: 480, damping: 38, mass: 0.65 }} />}
      <Icon className="size-[18px]" aria-hidden="true" /><span className="whitespace-nowrap">{label}</span>
    </Link>;
  })}</nav></LayoutGroup>;
}

function SidebarContent({ session, readiness, authDisabled, onNavigate }: { session: MeResponse; readiness: ReadyResponse | null; authDisabled: boolean; onNavigate?: () => void }) {
  const initials = session.user.display_name.split(/\s+/).map((part) => part[0]).join("").slice(0, 2).toUpperCase();
  return <div className="flex h-full flex-col bg-sidebar px-4 py-5">
    <Brand />
    {authDisabled && <div className="mt-5 rounded-lg border border-primary/20 bg-primary-subtle px-3 py-2 text-xs font-medium text-primary">Preview access · Auth disabled</div>}
    <Navigation onNavigate={onNavigate} />
    <div className="mt-auto border-t border-sidebar-border pt-4">
      <div className="rounded-lg border border-sidebar-border bg-sidebar-accent/40 p-3"><div className="flex items-center gap-2 text-sm font-medium text-sidebar-foreground"><Activity className="size-4" aria-hidden="true" />{readiness?.status === "ready" ? "Agent ready" : "Agent unavailable"}</div><p className="mt-1 text-xs leading-5 text-sidebar-muted">{readiness ? `Postgres ${readiness.dependencies.postgres} · Redis ${readiness.dependencies.redis} · Worker ${readiness.dependencies.worker}` : "Readiness could not be checked."}</p></div>
      <div className="mt-3 flex min-h-11 items-center gap-3 rounded-lg px-2"><span className="grid size-8 place-items-center rounded-full bg-accent text-xs font-semibold text-primary">{initials}</span><span className="min-w-0 flex-1"><span className="block truncate text-sm font-medium text-sidebar-foreground">{session.current_workspace.name}</span><span className="block truncate text-xs capitalize text-sidebar-muted">{session.user.display_name} · {session.current_workspace.role}</span></span>{!authDisabled && <form action={logoutAction}><button type="submit" className="rounded-md p-2 text-sidebar-muted hover:bg-sidebar-accent hover:text-sidebar-foreground" aria-label="Sign out"><LogOut className="size-4" aria-hidden="true" /></button></form>}</div>
    </div>
  </div>;
}

export function AppShell({ children, session, readiness, authDisabled = false }: { children: React.ReactNode; session: MeResponse; readiness: ReadyResponse | null; authDisabled?: boolean }) {
  const router = useRouter();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [commandOpen, setCommandOpen] = useState(false);
  useEffect(() => { const onKeyDown = (event: KeyboardEvent) => { if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") { event.preventDefault(); setCommandOpen((open) => !open); } }; window.addEventListener("keydown", onKeyDown); return () => window.removeEventListener("keydown", onKeyDown); }, []);
  const visit = (href: string) => { setCommandOpen(false); router.push(href); };

  return <div className="min-h-screen bg-background text-foreground lg:grid lg:grid-cols-[232px_minmax(0,1fr)]">
    <aside className="hidden min-h-screen border-r border-sidebar-border bg-sidebar lg:sticky lg:top-0 lg:block lg:h-screen"><SidebarContent session={session} readiness={readiness} authDisabled={authDisabled} /></aside>
    <div className="min-w-0">
      <header className="sticky top-0 z-40 flex h-16 items-center gap-3 border-b bg-card px-4 sm:px-6 lg:px-8">
        <Sheet open={mobileOpen} onOpenChange={setMobileOpen}><SheetTrigger render={<Button variant="outline" size="icon" className="lg:hidden" aria-label="Open navigation" />}><Menu className="size-5" /></SheetTrigger><SheetContent side="left" className="w-[280px] border-sidebar-border bg-sidebar p-0" showCloseButton={false}><SheetHeader className="sr-only"><SheetTitle>Navigation</SheetTitle><SheetDescription>Parallax workspace navigation</SheetDescription></SheetHeader><SidebarContent session={session} readiness={readiness} authDisabled={authDisabled} onNavigate={() => setMobileOpen(false)} /></SheetContent></Sheet>
        <button type="button" onClick={() => setCommandOpen(true)} className="flex min-h-10 min-w-0 flex-1 items-center gap-2 rounded-lg border border-transparent bg-surface-inset px-3 text-left text-sm text-muted-foreground hover:text-foreground sm:max-w-md"><Search className="size-4 shrink-0" aria-hidden="true" /><span className="truncate">Search workspace</span><kbd className="ml-auto hidden rounded border bg-muted px-1.5 py-0.5 font-mono text-xs sm:inline-flex">⌘K</kbd></button>
        {authDisabled && <span className="hidden rounded-md bg-primary-subtle px-2 py-1 text-xs font-medium text-primary sm:inline">Preview</span>}
        <Button variant="ghost" size="icon" aria-label="Notifications are not available" disabled><Bell className="size-[18px]" /></Button>
        <Button nativeButton={false} render={<Link href="/missions/new" />} className="min-h-10 gap-2"><Plus className="size-4" />New mission</Button>
      </header>
      <a href="#workspace-content" className="sr-only focus:not-sr-only focus:fixed focus:top-3 focus:left-3 focus:z-50 focus:rounded-lg focus:bg-card focus:p-3">Skip to content</a>
      <div id="workspace-content" data-workspace-content tabIndex={-1}>{children}</div>
    </div>
    <CommandDialog open={commandOpen} onOpenChange={setCommandOpen}><CommandInput placeholder="Search pages and actions" /><CommandList><CommandEmpty>No matching command.</CommandEmpty><CommandGroup heading="Navigate">{navigation.map(({ label, href, icon: Icon }) => <CommandItem key={href} onSelect={() => visit(href)}><Icon className="size-4" />{label}</CommandItem>)}</CommandGroup><CommandGroup heading="Actions"><CommandItem onSelect={() => visit("/missions/new")}><CommandIcon />Create a mission<CommandShortcut>↵</CommandShortcut></CommandItem></CommandGroup></CommandList></CommandDialog>
  </div>;
}
