// @vitest-environment jsdom
import React, { Suspense } from "react";
import { act, cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import { PanelSkeleton, PageSkeleton } from "./page-skeleton";

afterEach(cleanup);

describe("streaming loading states", () => {
  it("replaces the skeleton as soon as the resource resolves", async () => {
    let complete = false;
    let resolve!: () => void;
    const pending = new Promise<void>((done) => { resolve = done; });
    function Region() { if (!complete) throw pending; return <p>Mission data loaded</p>; }
    render(<Suspense fallback={<PanelSkeleton />}><Region /></Suspense>);
    expect(screen.getByLabelText("Loading panel").getAttribute("aria-busy")).toBe("true");
    await act(async () => { complete = true; resolve(); await pending; });
    expect(screen.queryByLabelText("Loading panel")).toBeNull();
    expect(screen.getByText("Mission data loaded")).toBeTruthy();
  });

  it("announces a page load without exposing decorative shapes", () => {
    const { container } = render(<PageSkeleton variant="dashboard" />);
    expect(screen.getByRole("status").getAttribute("aria-busy")).toBe("true");
    const shapes = container.querySelectorAll('[data-slot="skeleton"]');
    expect(shapes.length).toBeGreaterThan(20);
    expect([...shapes].every((shape) => shape.getAttribute("aria-hidden") === "true")).toBe(true);
  });
});
