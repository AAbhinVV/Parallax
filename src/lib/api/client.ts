import "server-only";

import createClient from "openapi-fetch";

import type { paths } from "@/generated/openapi";
import { ApiError, errorMessage } from "@/lib/api/errors";

export const API_URL = process.env.PARALLAX_API_URL || "http://localhost:8000";
const API_TIMEOUT_MS = 15_000;

export function createBackendClient(accessToken?: string, workspaceId?: string) {
  const headers: Record<string, string> = {
    "X-Correlation-ID": crypto.randomUUID(),
  };
  if (accessToken) headers.Authorization = `Bearer ${accessToken}`;
  if (workspaceId) headers["X-Workspace-ID"] = workspaceId;
  return createClient<paths>({
    baseUrl: API_URL,
    headers,
    fetch: async (request) => {
      try { return await fetch(request, { cache: "no-store", signal: AbortSignal.any([request.signal, AbortSignal.timeout(API_TIMEOUT_MS)]) }); }
      catch (error) {
        if (error instanceof DOMException && error.name === "TimeoutError") throw new ApiError("The Parallax API timed out.", 502, headers["X-Correlation-ID"]);
        if (error instanceof TypeError && error.message === "fetch failed") throw new ApiError("Cannot reach Parallax. Check that the local backend is running and try again.", 502, headers["X-Correlation-ID"]);
        throw error;
      }
    },
  });
}

export function unwrap<T>({ data, error, response }: { data?: T; error?: unknown; response: Response }): T {
  if (data !== undefined) return data;
  const detail = typeof error === "object" && error && "detail" in error && typeof error.detail === "string" ? error.detail : undefined;
  throw new ApiError(
    errorMessage(response.status, detail),
    response.status,
    response.headers.get("X-Correlation-ID") ?? undefined,
    response.headers.get("X-Trace-ID") ?? undefined,
    error,
  );
}
