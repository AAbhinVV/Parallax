export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
    public readonly correlationId?: string,
    public readonly traceId?: string,
    public readonly details?: unknown,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export function errorMessage(status: number, detail?: string) {
  if (detail) return detail;
  if (status === 401) return "Your session has expired. Sign in again.";
  if (status === 403) return "Your workspace role does not permit this action.";
  if (status === 404) return "The requested resource was not found.";
  if (status === 409) return "The resource changed or this action has already been decided.";
  if (status === 422) return "The request contains invalid data.";
  if (status === 502) return "A connected provider could not complete the request.";
  return `The API returned status ${status}.`;
}
