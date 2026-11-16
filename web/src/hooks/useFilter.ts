import { useState, useMemo } from "react";
import type { Tombstone, Severity } from "../types/report";

export type SortKey = keyof Pick<
  Tombstone,
  "resource_name" | "resource_type" | "region" | "severity" | "cause" | "detected_at" | "estimated_monthly_cost"
>;
export type SortDir = "asc" | "desc";

interface FilterState {
  types: string[];
  regions: string[];
  severities: Severity[];
}

export function useFilter(tombstones: Tombstone[]) {
  const [filters, setFilters] = useState<FilterState>({
    types: [],
    regions: [],
    severities: [],
  });
  const [sortKey, setSortKey] = useState<SortKey>("estimated_monthly_cost");
  const [sortDir, setSortDir] = useState<SortDir>("desc");

  const allTypes = useMemo(
    () => Array.from(new Set(tombstones.map((t) => t.resource_type))).sort(),
    [tombstones]
  );
  const allRegions = useMemo(
    () => Array.from(new Set(tombstones.map((t) => t.region))).sort(),
    [tombstones]
  );

  const filtered = useMemo(() => {
    return tombstones.filter((t) => {
      if (filters.types.length && !filters.types.includes(t.resource_type)) return false;
      if (filters.regions.length && !filters.regions.includes(t.region)) return false;
      if (filters.severities.length && !filters.severities.includes(t.severity)) return false;
      return true;
    });
  }, [tombstones, filters]);

  const sorted = useMemo(() => {
    return [...filtered].sort((a, b) => {
      const av = a[sortKey] ?? "";
      const bv = b[sortKey] ?? "";
      let cmp = 0;
      if (typeof av === "number" && typeof bv === "number") {
        cmp = av - bv;
      } else {
        cmp = String(av).localeCompare(String(bv));
      }
      return sortDir === "asc" ? cmp : -cmp;
    });
  }, [filtered, sortKey, sortDir]);

  function toggleSort(key: SortKey) {
    if (key === sortKey) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(key);
      setSortDir("desc");
    }
  }

  function toggleFilter<K extends keyof FilterState>(
    field: K,
    value: FilterState[K][number]
  ) {
    setFilters((prev) => {
      const arr = prev[field] as string[];
      const next = arr.includes(value as string)
        ? arr.filter((x) => x !== value)
        : [...arr, value as string];
      return { ...prev, [field]: next };
    });
  }

  function clearFilters() {
    setFilters({ types: [], regions: [], severities: [] });
  }

  return {
    filtered: sorted,
    filters,
    sortKey,
    sortDir,
    allTypes,
    allRegions,
    toggleSort,
    toggleFilter,
    clearFilters,
    count: sorted.length,
  };
}
