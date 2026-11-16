import { describe, it, expect, vi, afterEach } from "vitest";
import { prefersReducedMotion } from "./motion";

describe("prefersReducedMotion", () => {
  afterEach(() => vi.restoreAllMocks());
  it("is false when matchMedia is missing", () => {
    const orig = window.matchMedia;
    // @ts-expect-error simulate absence
    window.matchMedia = undefined;
    expect(prefersReducedMotion()).toBe(false);
    window.matchMedia = orig;
  });
  it("reflects the media query", () => {
    window.matchMedia = vi.fn().mockReturnValue({ matches: true }) as unknown as typeof window.matchMedia;
    expect(prefersReducedMotion()).toBe(true);
  });
});
