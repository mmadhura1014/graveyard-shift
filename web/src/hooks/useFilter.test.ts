import { describe, it, expect } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useFilter } from "./useFilter";
import type { Tombstone } from "../types/report";

function makeTombstone(overrides: Partial<Tombstone>): Tombstone {
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

const tombstones: Tombstone[] = [
  makeTombstone({ id: "1", resource_id: "vol-1", severity: "wasteful", estimated_monthly_cost: 40, region: "us-east-1", resource_type: "EC2::Volume" }),
  makeTombstone({ id: "2", resource_id: "eip-1", severity: "wasteful", estimated_monthly_cost: 3.65, region: "us-east-1", resource_type: "EC2::EIP" }),
  makeTombstone({ id: "3", resource_id: "key-1", severity: "risky",    estimated_monthly_cost: 0,    region: "global",    resource_type: "IAM::AccessKey", exorcism_cli: "aws iam delete-access-key --access-key-id key-1 --user-name u" }),
  makeTombstone({ id: "4", resource_id: "sg-1",  severity: "harmless", estimated_monthly_cost: 0,    region: "eu-west-1", resource_type: "EC2::SecurityGroup" }),
];

describe("useFilter", () => {
  it("returns all tombstones with no filters", () => {
    const { result } = renderHook(() => useFilter(tombstones));
    expect(result.current.filtered).toHaveLength(4);
  });

  it("sorts by cost descending by default", () => {
    const { result } = renderHook(() => useFilter(tombstones));
    const costs = result.current.filtered.map((t) => t.estimated_monthly_cost);
    expect(costs[0]).toBe(40);
    expect(costs[costs.length - 1]).toBe(0);
  });

  it("sorts ascending after toggle", () => {
    const { result } = renderHook(() => useFilter(tombstones));
    act(() => result.current.toggleSort("estimated_monthly_cost"));
    const costs = result.current.filtered.map((t) => t.estimated_monthly_cost);
    expect(costs[0]).toBe(0);
  });

  it("filters by severity", () => {
    const { result } = renderHook(() => useFilter(tombstones));
    act(() => result.current.toggleFilter("severities", "risky"));
    expect(result.current.filtered).toHaveLength(1);
    expect(result.current.filtered[0].severity).toBe("risky");
  });

  it("filters by type", () => {
    const { result } = renderHook(() => useFilter(tombstones));
    act(() => result.current.toggleFilter("types", "EC2::Volume"));
    expect(result.current.filtered).toHaveLength(1);
  });

  it("filters by region", () => {
    const { result } = renderHook(() => useFilter(tombstones));
    act(() => result.current.toggleFilter("regions", "eu-west-1"));
    expect(result.current.filtered).toHaveLength(1);
    expect(result.current.filtered[0].region).toBe("eu-west-1");
  });

  it("clearFilters resets to all tombstones", () => {
    const { result } = renderHook(() => useFilter(tombstones));
    act(() => result.current.toggleFilter("severities", "risky"));
    expect(result.current.filtered).toHaveLength(1);
    act(() => result.current.clearFilters());
    expect(result.current.filtered).toHaveLength(4);
  });

  it("count matches filtered length", () => {
    const { result } = renderHook(() => useFilter(tombstones));
    act(() => result.current.toggleFilter("severities", "harmless"));
    expect(result.current.count).toBe(result.current.filtered.length);
  });
});
