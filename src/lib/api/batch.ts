import { ApiError } from "@/lib/api/errors";

export type BatchFailure = { message: string; status: number; correlationId?: string; traceId?: string };

export function assembleBatch(keys: readonly string[], results: readonly PromiseSettledResult<unknown>[]) {
  const data: Record<string, unknown> = {};
  const errors: Record<string, BatchFailure> = {};
  results.forEach((result, index) => {
    const key = keys[index];
    if (result.status === "fulfilled") data[key] = result.value;
    else {
      const error = result.reason;
      errors[key] = { message: error instanceof Error ? error.message : "Request failed", status: error instanceof ApiError ? error.status : 500, correlationId: error instanceof ApiError ? error.correlationId : undefined, traceId: error instanceof ApiError ? error.traceId : undefined };
    }
  });
  const failures = Object.values(errors);
  const status = Object.keys(data).length === 0 && failures.length > 0 ? ([401, 403, 404].find((code) => failures.every((error) => error.status === code)) ?? 502) : 200;
  return { data, errors, status };
}
