import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { ShareCard } from "./ShareCard";
import type { Report } from "../types/report";

describe("ShareCard", () => {
  it("renders the button with an honest note about uploads or missing canvas support", () => {
    const report = {
      demo: true,
      tombstones: [],
      summary: { estimated_monthly_cost: 0, total_tombstones: 0 },
    } as unknown as Report;
    render(<ShareCard report={report} />);
    expect(screen.getByRole("button", { name: /share my graveyard/i })).toBeTruthy();
    expect(screen.getByText(/nothing is uploaded|isn't available/i)).toBeTruthy();
  });
});
