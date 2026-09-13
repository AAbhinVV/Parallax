"use client";

import { CircleAlert, RotateCcw } from "lucide-react";

import { Button } from "@/components/ui/button";

export default function WorkspaceError({ reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return (
    <div className="mx-auto flex min-h-[60vh] max-w-xl items-center px-4 py-12 sm:px-6">
      <div className="w-full border bg-card p-6 sm:p-8">
        <CircleAlert className="size-6 text-destructive" aria-hidden="true" />
        <h1 className="mt-5 text-xl font-semibold">This view could not be loaded</h1>
        <p className="mt-2 text-sm leading-6 text-muted-foreground">
          The frontend kept your current route. Retry the request, and check the API URL if the issue continues.
        </p>
        <Button className="mt-6 gap-2" onClick={reset}>
          <RotateCcw className="size-4" aria-hidden="true" />
          Try again
        </Button>
      </div>
    </div>
  );
}
