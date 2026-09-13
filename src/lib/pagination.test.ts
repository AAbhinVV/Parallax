import { describe, expect, it } from "vitest";
import { hasNextPage, pageNumber, pageOffset, pollingDelay } from "@/lib/pagination";

describe("URL pagination", () => {
  it("normalizes invalid pages and calculates offsets", () => { expect(pageNumber("bad")).toBe(1); expect(pageNumber("-2")).toBe(1); expect(pageOffset(3, 20)).toBe(40); });
  it("only exposes next when a page is full", () => { expect(hasNextPage(20, 20)).toBe(true); expect(hasNextPage(19, 20)).toBe(false); });
});

describe("polling backoff", () => { it("backs off after a failure", () => { expect(pollingDelay(0, 2_000)).toBe(2_000); expect(pollingDelay(1, 2_000)).toBe(30_000); }); });
