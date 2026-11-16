import { describe, it, expect } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { HowScoreWorks } from "./HowScoreWorks";
import { HeadlineBar } from "./HeadlineBar";

describe("HowScoreWorks", () => {
  it("toggles the explanation and closes on Escape", () => {
    render(<HowScoreWorks />);
    const btn = screen.getByRole("button", { name: /how is this calculated/i });
    expect(btn.getAttribute("aria-expanded")).toBe("false");
    fireEvent.click(btn);
    expect(btn.getAttribute("aria-expanded")).toBe("true");
    expect(screen.getByRole("region").textContent).toMatch(/heuristic/i);
    fireEvent.keyDown(btn, { key: "Escape" });
    expect(btn.getAttribute("aria-expanded")).toBe("false");
  });
});

describe("HeadlineBar score", () => {
  it("shows the score and label for the demo-like summary", () => {
    render(
      <HeadlineBar
        demo={false}
        securityCount={5}
        summary={{
          total_tombstones: 18,
          estimated_monthly_cost: 202.15,
          undead_credentials_count: 3,
          by_severity: { harmless: 2, wasteful: 13, risky: 3 },
          by_type: {},
        }}
      />,
    );
    expect(screen.getByText(/53\/100 · Haunted/)).toBeTruthy();
  });
});
