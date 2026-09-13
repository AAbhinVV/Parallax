"use client";

import Link from "next/link";
import { useActionState, useState } from "react";
import { Eye, EyeOff } from "lucide-react";

import { loginAction, registerAction, type AuthActionState } from "@/app/actions/auth";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

const initialState: AuthActionState = {};

export function AuthForm({ mode }: { mode: "login" | "register" }) {
  const action = mode === "login" ? loginAction : registerAction;
  const [state, formAction, pending] = useActionState(action, initialState);
  const register = mode === "register";
  const [showPassword, setShowPassword] = useState(false);

  return (
    <form action={formAction} aria-busy={pending} className="space-y-4">
      {register ? (
        <>
          <Field label="Display name" name="display_name" defaultValue={state.fields?.display_name} autoComplete="name" />
          <Field label="Workspace name" name="workspace_name" defaultValue={state.fields?.workspace_name} autoComplete="organization" />
          <Field label="Workspace slug" name="workspace_slug" defaultValue={state.fields?.workspace_slug} pattern="[a-z0-9]+(?:-[a-z0-9]+)*" />
        </>
      ) : null}
      <Field label="Email" name="email" type="email" defaultValue={state.fields?.email} autoComplete="email" />
      <div className="space-y-2"><Label htmlFor="password">Password</Label><div className="relative"><Input id="password" name="password" required type={showPassword ? "text" : "password"} minLength={register ? 12 : 1} autoComplete={register ? "new-password" : "current-password"} className="pr-11" aria-describedby={register ? "password-hint" : undefined} /><button type="button" aria-label={showPassword ? "Hide password" : "Show password"} aria-pressed={showPassword} onClick={() => setShowPassword(!showPassword)} className="absolute inset-y-0 right-0 grid w-10 place-items-center rounded-lg text-muted-foreground hover:text-foreground">{showPassword ? <EyeOff className="size-4" /> : <Eye className="size-4" />}</button></div>{register && <p id="password-hint" className="text-xs text-muted-foreground">Use at least 12 characters.</p>}</div>
      {!register ? <Field label="Workspace ID (optional)" name="workspace_id" defaultValue={state.fields?.workspace_id} /> : null}
      {state.error ? (
        <div role="alert" className="rounded-lg border border-destructive/25 bg-danger-soft p-3 text-sm text-destructive">
          {state.error}{state.correlationId ? <span className="mt-1 block font-mono text-xs">Reference {state.correlationId}</span> : null}
        </div>
      ) : null}
      <Button className="h-11 w-full" type="submit" disabled={pending}>{pending ? "Submitting…" : register ? "Create workspace" : "Sign in"}</Button>
      <p className="text-center text-sm text-muted-foreground">
        {register ? "Already have an account? " : "Need a workspace? "}
        <Link className="font-medium text-primary hover:underline" href={register ? "/login" : "/register"}>{register ? "Sign in" : "Register"}</Link>
      </p>
    </form>
  );
}

function Field({ label, name, ...props }: React.ComponentProps<typeof Input> & { label: string; name: string }) {
  return <div className="space-y-2"><Label htmlFor={name}>{label}</Label><Input key={String(props.defaultValue ?? "")} id={name} name={name} required={name !== "workspace_id"} {...props} /></div>;
}
