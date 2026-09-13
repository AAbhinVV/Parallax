"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

export function SessionRefresher({ expiresAt }: { expiresAt: number }) {
  const router = useRouter();
  useEffect(() => {
    if (!expiresAt) return;
    const delay = Math.max(5_000, expiresAt - Date.now() - 60_000);
    const timer = window.setTimeout(async () => {
      const response = await fetch("/api/session/refresh", { method: "POST", cache: "no-store" });
      if (response.status === 401) router.replace("/login");
      else if (response.ok) router.refresh();
    }, delay);
    return () => window.clearTimeout(timer);
  }, [expiresAt, router]);
  return null;
}
