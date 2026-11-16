import { describe, it, expect } from "vitest";
import { buildShareCardData, EMPTY_CARD_TEXT } from "./shareCard";
import type { Report, Tombstone } from "../types/report";

function stone(overrides: Partial<Tombstone>): Tombstone {
  return {
    id: "id-1",
    resource_id: "res-1",
    resource_name: "test",
    resource_type: "EC2::Volume",
    region: "us-east-1",
    account_id: "111122223333",
    cause: "abandoned",
    severity: "wasteful",
    detected_at: "2025-07-01T10:00:00Z",
    created_at: null,
    estimated_monthly_cost: 10,
    metadata: {},
    exorcism_cli: "aws ec2 delete-volume --volume-id res-1 --dry-run",
    exorcism_tf: "",
    ...overrides,
  };
}

function report(tombstones: Tombstone[], cost = 0): Report {
  return {
    schema_version: "1.0",
    generated_at: "2025-07-01T10:00:00Z",
    demo: true,
    account_id: "111122223333",
    regions_scanned: ["us-east-1"],
    scan_duration_seconds: 0.1,
    tombstones,
    summary: {
      total_tombstones: tombstones.length,
      estimated_monthly_cost: cost,
      undead_credentials_count: 0,
      by_severity: { harmless: 0, wasteful: tombstones.length, risky: 0 },
      by_type: {},
    },
  };
}

describe("buildShareCardData", () => {
  it("returns the score and label derived from the report", () => {
    const r = report([stone({ resource_id: "a", estimated_monthly_cost: 40 })], 40);
    const d = buildShareCardData(r);
    expect(d.score).toBeGreaterThanOrEqual(0);
    expect(d.score).toBeLessThanOrEqual(100);
    expect(["Peaceful", "Restless", "Haunted", "Cursed"]).toContain(d.label);
  });

  it("returns totalCost from the summary", () => {
    const r = report([stone({ resource_id: "a" })], 202.15);
    expect(buildShareCardData(r).totalCost).toBe(202.15);
  });

  it("returns up to 3 names, highest cost first", () => {
    const r = report([
      stone({ resource_id: "a", resource_name: "cheap", estimated_monthly_cost: 1 }),
      stone({ resource_id: "b", resource_name: "pricey", estimated_monthly_cost: 100 }),
      stone({ resource_id: "c", resource_name: "mid", estimated_monthly_cost: 50 }),
      stone({ resource_id: "d", resource_name: "also", estimated_monthly_cost: 75 }),
    ]);
    expect(buildShareCardData(r).topNames).toEqual(["pricey", "also", "mid"]);
  });

  it("returns fewer names when fewer than 3 tombstones exist", () => {
    const r = report([stone({ resource_id: "a", resource_name: "only" })]);
    expect(buildShareCardData(r).topNames).toEqual(["only"]);
  });

  it("marks empty=true and returns no names when there are no tombstones", () => {
    const d = buildShareCardData(report([]));
    expect(d.empty).toBe(true);
    expect(d.topNames).toEqual([]);
    expect(EMPTY_CARD_TEXT).toBe("Your graveyard is peaceful.");
  });

  it("uses the short type label (not an identifier) when resource_name is null", () => {
    const r = report([stone({ resource_id: "vol-0abc", resource_name: null, resource_type: "EC2::Volume" })]);
    expect(buildShareCardData(r).topNames).toEqual(["Volume"]);
  });

  it("never exposes account_id, resource_id, keys, IPs or ARNs in the output", () => {
    const r = report([
      stone({
        resource_id: "vol-0SECRETID",
        resource_name: "named",
        account_id: "111122223333",
        metadata: { public_ip: "203.0.113.10", key_id: "AKIAIOSFODNN7EXAMPLE" },
      }),
    ]);
    const d = buildShareCardData(r);
    const blob = JSON.stringify(d);
    expect(blob).not.toContain("vol-0SECRETID");
    expect(blob).not.toContain("111122223333");
    expect(blob).not.toContain("203.0.113.10");
    expect(blob).not.toContain("AKIA");
    expect(blob).toContain("named");
  });

  it("is pure (same input -> same output, no report mutation)", () => {
    const r = report([stone({ resource_id: "a", resource_name: "x", estimated_monthly_cost: 5 })], 5);
    const snapshot = JSON.parse(JSON.stringify(r));
    const d1 = buildShareCardData(r);
    const d2 = buildShareCardData(r);
    expect(d1).toEqual(d2);
    expect(r).toEqual(snapshot);
  });

  it("counts IAM keys and security groups as security-related for the score", () => {
    // 6 security tombstones -> security component capped at 15
    const r = report(
      Array.from({ length: 6 }, (_, i) =>
        stone({ resource_id: `k${i}`, resource_type: "IAM::AccessKey", estimated_monthly_cost: 0 }),
      ),
      0,
    );
    const d = buildShareCardData(r);
    // volume 6 + security 15 + cost 0 = 21 -> Restless
    expect(d.score).toBe(21);
    expect(d.label).toBe("Restless");
  });
});
