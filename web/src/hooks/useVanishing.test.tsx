import { describe, it, expect } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useVanishing } from "./useVanishing";
import { useReportStore } from "../store/reportStore";

describe("useVanishing", () => {
  it("turns on only for the exorcised resource", () => {
    const a = renderHook(() => useVanishing("r-a"));
    const b = renderHook(() => useVanishing("r-b"));
    expect(a.result.current).toBe(false);
    act(() => useReportStore.getState().exorcise("r-a"));
    expect(a.result.current).toBe(true);
    expect(b.result.current).toBe(false);
  });
});
