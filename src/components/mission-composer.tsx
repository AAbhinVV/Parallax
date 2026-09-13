"use client";

import { useActionState, useState } from "react";
import { ArrowUp, Terminal } from "lucide-react";

import { createMissionAction, type MutationState } from "@/app/actions/missions";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import type { Project } from "@/lib/api/types";

const initialState: MutationState = {};

export function MissionComposer({ projects, suggestedPrompt, autoFocus = false }: { projects: Project[]; suggestedPrompt?: string; autoFocus?: boolean }) {
  const [state, action, pending] = useActionState(createMissionAction, initialState);
  const [idempotencyKey] = useState(() => crypto.randomUUID());

  return <section className="rounded-lg border bg-card p-4 focus-within:border-primary sm:p-5" aria-labelledby="composer-title">
    <form action={action} aria-busy={pending}>
      <input type="hidden" name="idempotency_key" value={idempotencyKey} />
      <div className="flex gap-3">
        <span className="grid size-9 shrink-0 place-items-center rounded-md bg-accent text-primary"><Terminal className="size-4" aria-hidden="true" /></span>
        <div className="min-w-0 flex-1">
          <label id="composer-title" htmlFor="mission-prompt" className="text-sm font-semibold">Tell Parallax what needs to be done</label>
          <Textarea id="mission-prompt" name="prompt" required minLength={3} maxLength={10_000} autoFocus={autoFocus} defaultValue={suggestedPrompt} placeholder="Review the Payments project, find blockers, and prepare an update…" className="mt-2 min-h-24 resize-y border-0 bg-transparent px-0 shadow-none focus-visible:ring-0" />
          <div className="mt-3 flex flex-col gap-3 border-t pt-3 sm:flex-row sm:items-center">
            <label className="sr-only" htmlFor="mission-project">Project</label>
            <select id="mission-project" name="project" className="min-h-9 rounded-lg border bg-background px-3 text-sm">
              <option value="General">General</option>
              {projects.map((project) => <option key={project.id} value={project.name}>{project.name}</option>)}
            </select>
            <Button type="submit" className="sm:ml-auto" disabled={pending}>{pending ? "Creating…" : "Create mission"}<ArrowUp className="size-4" /></Button>
          </div>
          {state.error && <p role="alert" className="mt-3 text-sm text-destructive">{state.error}{state.correlationId ? ` Support ID: ${state.correlationId}` : ""}</p>}
        </div>
      </div>
    </form>
  </section>;
}
