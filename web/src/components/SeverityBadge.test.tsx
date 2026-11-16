import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { SeverityBadge } from "./SeverityBadge";

describe("SeverityBadge", () => {
  it("renders Harmless text for harmless severity", () => {
    render(<SeverityBadge severity="harmless" />);
    expect(screen.getByText("Harmless")).toBeTruthy();
  });

  it("renders Wasteful text for wasteful severity", () => {
    render(<SeverityBadge severity="wasteful" />);
    expect(screen.getByText("Wasteful")).toBeTruthy();
  });

  it("renders Risky text for risky severity", () => {
    render(<SeverityBadge severity="risky" />);
    expect(screen.getByText("Risky")).toBeTruthy();
  });

  it("applies harmless CSS class", () => {
    const { container } = render(<SeverityBadge severity="harmless" />);
    expect(container.querySelector(".badge-harmless")).toBeTruthy();
  });

  it("applies wasteful CSS class", () => {
    const { container } = render(<SeverityBadge severity="wasteful" />);
    expect(container.querySelector(".badge-wasteful")).toBeTruthy();
  });

  it("applies risky CSS class", () => {
    const { container } = render(<SeverityBadge severity="risky" />);
    expect(container.querySelector(".badge-risky")).toBeTruthy();
  });
});
