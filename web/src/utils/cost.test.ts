import { describe, it, expect } from "vitest";
import { formatCost, formatCostShort } from "./cost";

describe("formatCost", () => {
  it("formats zero cost", () => expect(formatCost(0)).toBe("$0.00/mo (estimated)"));
  it("formats positive cost", () => expect(formatCost(32.85)).toBe("$32.85/mo (estimated)"));
  it("includes estimated label", () => expect(formatCost(10)).toContain("estimated"));
});

describe("formatCostShort", () => {
  it("returns dash for zero", () => expect(formatCostShort(0)).toBe("–"));
  it("formats positive cost without estimated label", () => {
    expect(formatCostShort(3.65)).toBe("$3.65/mo");
  });
});
