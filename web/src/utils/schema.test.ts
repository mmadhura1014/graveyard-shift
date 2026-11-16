import { describe, it, expect } from "vitest";
import { validateReport } from "./schema";
import demoReport from "../assets/demo-report.json";

describe("validateReport", () => {
  it("accepts the bundled demo report", () => {
    const result = validateReport(demoReport);
    expect(result).not.toBeNull();
    expect(result?.demo).toBe(true);
  });

  it("returns null for an empty object", () => {
    expect(validateReport({})).toBeNull();
  });

  it("returns null for a string", () => {
    expect(validateReport("not a report")).toBeNull();
  });

  it("returns null for null", () => {
    expect(validateReport(null)).toBeNull();
  });

  it("returns null when required fields are missing", () => {
    const bad = { schema_version: "1.0", generated_at: "2025-07-01T10:00:00Z" };
    expect(validateReport(bad)).toBeNull();
  });

  it("returns null when severity has wrong enum value", () => {
    const clone = JSON.parse(JSON.stringify(demoReport));
    clone.tombstones[0].severity = "nuclear";
    expect(validateReport(clone)).toBeNull();
  });

  it("returns null when estimated_monthly_cost is negative", () => {
    const clone = JSON.parse(JSON.stringify(demoReport));
    clone.tombstones[0].estimated_monthly_cost = -1;
    expect(validateReport(clone)).toBeNull();
  });
});
