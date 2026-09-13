import { afterEach, describe, expect, it } from "vitest";
import { NextRequest } from "next/server";

import { proxy } from "@/proxy";

describe("protected-route proxy", () => {
  afterEach(() => { delete process.env.PARALLAX_DISABLE_AUTH; });

  it("allows workspace routes when the local auth bypass is enabled", () => {
    process.env.PARALLAX_DISABLE_AUTH = "true";
    const response = proxy(new NextRequest("http://localhost:3000/dashboard"));
    expect(response.headers.get("x-middleware-next")).toBe("1");
  });

  it("allows a valid access session", () => {
    const request = new NextRequest("http://localhost:3000/dashboard", { headers: { cookie: `parallax_access=access; parallax_refresh=refresh; parallax_access_expires=${Date.now() + 60_000}` } });
    expect(proxy(request).headers.get("x-middleware-next")).toBe("1");
  });

  it("routes an expired access session through refresh", () => {
    const request = new NextRequest("http://localhost:3000/missions?page=2", { headers: { cookie: "parallax_access=access; parallax_refresh=refresh; parallax_access_expires=1" } });
    const response = proxy(request);
    expect(response.status).toBe(307);
    expect(response.headers.get("location")).toContain("/api/session/refresh?next=%2Fmissions%3Fpage%3D2");
  });

  it("redirects missing sessions to login", () => {
    const response = proxy(new NextRequest("http://localhost:3000/projects"));
    expect(response.headers.get("location")).toBe("http://localhost:3000/login");
  });
});
