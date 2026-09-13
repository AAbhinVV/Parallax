import { describe, expect, it } from "vitest";

import { assembleBatch } from "@/lib/api/batch";
import { ApiError } from "@/lib/api/errors";

describe("BFF batch responses", () => {
  it("keeps successful resources when another endpoint fails", () => {
    const output = assembleBatch(["stats", "activity"], [{ status: "fulfilled", value: { active: 2 } }, { status: "rejected", reason: new ApiError("failed", 502, "cid", "tid") }]);
    expect(output.status).toBe(200);
    expect(output.data.stats).toEqual({ active: 2 });
    expect(output.errors.activity).toMatchObject({ status: 502, correlationId: "cid", traceId: "tid" });
  });

  it("propagates all-resource authentication and not-found failures", () => {
    expect(assembleBatch(["one"], [{ status: "rejected", reason: new ApiError("expired", 401) }]).status).toBe(401);
    expect(assembleBatch(["one"], [{ status: "rejected", reason: new ApiError("missing", 404) }]).status).toBe(404);
  });
});
