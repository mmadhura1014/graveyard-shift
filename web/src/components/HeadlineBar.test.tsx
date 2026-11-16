import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { HeadlineBar } from "./HeadlineBar";
import type { ReportSummary } from "../types/report";

const summary: ReportSummary = {
  total_tombstones: 18,
  estimated_monthly_cost: 202.15,
  undead_credentials_count: 3,
  by_severity: { harmless: 2, wasteful: 13, risky: 3 },
  by_type: { "EC2::Volume": 3 },
};

describe("HeadlineBar", () => {
  it("shows tombstone count", () => {
    render(<HeadlineBar summary={summary} demo={false} />);
    expect(screen.getByText("18")).toBeTruthy();
  });

  it("shows estimated monthly cost", () => {
    render(<HeadlineBar summary={summary} demo={false} />);
    expect(screen.getByText("$202.15/mo")).toBeTruthy();
  });

  it("shows undead credentials count", () => {
    render(<HeadlineBar summary={summary} demo={false} />);
    expect(screen.getByText("3")).toBeTruthy();
  });

  it("shows Sample Data badge when demo is true", () => {
    render(<HeadlineBar summary={summary} demo={true} />);
    expect(screen.getByText("🎃 Sample Data")).toBeTruthy();
  });

  it("hides Sample Data badge when demo is false", () => {
    render(<HeadlineBar summary={summary} demo={false} />);
    expect(screen.queryByText("🎃 Sample Data")).toBeNull();
  });
});
