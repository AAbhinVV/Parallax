import { AppShell } from "@/components/app-shell";
import { SessionRefresher } from "@/components/session-refresher";
import { getReady, requireSession } from "@/lib/api/server";
import { authDisabled } from "@/lib/auth/preview";

async function AuthenticatedWorkspace({ children }: { children: React.ReactNode }) {
  const [session, readiness] = await Promise.all([requireSession(), getReady().catch(() => null)]);
  return <AppShell session={session} readiness={readiness} authDisabled={authDisabled}>{!authDisabled && <SessionRefresher expiresAt={session.expiresAt} />}{children}</AppShell>;
}

export default function WorkspaceLayout({ children }: { children: React.ReactNode }) {
  return <Suspense fallback={<ShellSkeleton />}><AuthenticatedWorkspace>{children}</AuthenticatedWorkspace></Suspense>;
}
import { Suspense } from "react";
import { ShellSkeleton } from "@/components/page-skeleton";
