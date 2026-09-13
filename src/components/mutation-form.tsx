"use client";

import { useActionState } from "react";

import type { MutationState } from "@/app/actions/missions";
import { Button } from "@/components/ui/button";

type MutationAction = (state: MutationState, formData: FormData) => Promise<MutationState>;

export function MutationForm({ action, label, pendingLabel = "Working…", variant = "default", className, children }: {
  action: MutationAction;
  label: string;
  pendingLabel?: string;
  variant?: "default" | "outline" | "destructive" | "ghost";
  className?: string;
  children?: React.ReactNode;
}) {
  const [state, formAction, pending] = useActionState(action, {});
  return <form action={formAction} className={className}>
    {children}
    <Button type="submit" variant={variant} className="w-full" disabled={pending}>{pending ? pendingLabel : label}</Button>
    {state.error && <p role="alert" className="mt-2 text-sm text-destructive">{state.error}{state.correlationId && <span className="mt-1 block font-mono text-xs">Reference {state.correlationId}</span>}</p>}
  </form>;
}
