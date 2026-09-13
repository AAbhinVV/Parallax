import { describe, expect, it } from "vitest";
import { ApiError, errorMessage } from "@/lib/api/errors";

describe("API errors", () => {
  it("maps actionable status messages", () => { expect(errorMessage(401)).toMatch(/session/i); expect(errorMessage(409)).toMatch(/changed|conflict/i); expect(errorMessage(502)).toMatch(/provider|integration|upstream/i); });
  it("preserves support diagnostics", () => { const error = new ApiError("failed", 502, "correlation", "trace"); expect(error.correlationId).toBe("correlation"); expect(error.traceId).toBe("trace"); });
});
