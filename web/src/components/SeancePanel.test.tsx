import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, cleanup, act } from "@testing-library/react";
import { SeancePanel } from "./SeancePanel";
import type { Tombstone } from "../types/report";
import { useReportStore } from "../store/reportStore";

function stone(overrides: Partial<Tombstone> = {}): Tombstone {
  return {
    id: "id-1",
    resource_id: "vol-0abc",
    resource_name: "old-volume",
    resource_type: "EC2::Volume",
    region: "us-east-1",
    account_id: "111122223333",
    cause: "abandoned",
    severity: "wasteful",
    detected_at: "2025-07-01T10:00:00Z",
    created_at: "2023-12-29T10:00:00Z",
    estimated_monthly_cost: 40,
    metadata: { size_gib: 100, volume_type: "gp2" },
    exorcism_cli: "aws ec2 delete-volume --volume-id vol-0abc --dry-run",
    exorcism_tf: "",
    ...overrides,
  };
}

// Fresh trigger mock per test (focus-return verification must not leak across tests).
function makeTrigger(): HTMLElement {
  return { focus: vi.fn() } as unknown as HTMLElement;
}

beforeEach(() => {
  cleanup();
  vi.clearAllMocks();
  useReportStore.setState({ exorcisedResourceId: null, exorcismNonce: 0 });
});

describe("SeancePanel", () => {
  it("renders as a dialog with aria-modal", () => {
    render(<SeancePanel tombstone={stone()} triggerEl={makeTrigger()} onClose={vi.fn()} />);
    const dialog = screen.getByRole("dialog");
    expect(dialog).toHaveAttribute("aria-modal", "true");
  });

  it("has an accessible title (aria-labelledby)", () => {
    render(<SeancePanel tombstone={stone()} triggerEl={makeTrigger()} onClose={vi.fn()} />);
    const dialog = screen.getByRole("dialog");
    const labelledBy = dialog.getAttribute("aria-labelledby");
    expect(labelledBy).toBeTruthy();
    expect(document.getElementById(labelledBy!)).not.toBeNull();
  });

  it("renders the story parts (age, cost, cause, attached, flavor)", () => {
    render(<SeancePanel tombstone={stone()} triggerEl={makeTrigger()} onClose={vi.fn()} />);
    expect(screen.getByText(/Died/)).toBeTruthy();
    expect(screen.getByText(/Still costs you \$40\.00\/month\. \(estimated\)/)).toBeTruthy();
    expect(screen.getByText("Cause of death: abandoned.")).toBeTruthy();
    expect(screen.getByText(/It still reserves 100 GiB of gp2 storage\./)).toBeTruthy();
  });

  it("renders a 'Copy cleanup command' button that calls exorcise on copy", async () => {
    render(<SeancePanel tombstone={stone()} triggerEl={makeTrigger()} onClose={vi.fn()} />);
    const btn = screen.getByRole("button", { name: /Copy cleanup command/i });
    // clipboard.writeText is async (stubbed in test-setup); flush the microtask with act.
    await act(async () => {
      fireEvent.click(btn);
    });
    expect(useReportStore.getState().exorcisedResourceId).toBe("vol-0abc");
    expect(useReportStore.getState().exorcismNonce).toBe(1);
  });

  it("calls onClose and returns focus to the trigger on Close button", () => {
    const trigger = makeTrigger();
    const onClose = vi.fn();
    render(<SeancePanel tombstone={stone()} triggerEl={trigger} onClose={onClose} />);
    const closeBtn = screen.getByRole("button", { name: /Close séance panel/i });
    fireEvent.click(closeBtn);
    expect(onClose).toHaveBeenCalledTimes(1);
    expect((trigger.focus as ReturnType<typeof vi.fn>)).toHaveBeenCalledTimes(1);
  });

  it("calls onClose and returns focus when Escape is pressed", () => {
    const trigger = makeTrigger();
    const onClose = vi.fn();
    render(<SeancePanel tombstone={stone()} triggerEl={trigger} onClose={onClose} />);
    const dialog = screen.getByRole("dialog");
    fireEvent.keyDown(dialog, { key: "Escape" });
    expect(onClose).toHaveBeenCalledTimes(1);
    expect((trigger.focus as ReturnType<typeof vi.fn>)).toHaveBeenCalledTimes(1);
  });

  it("omits the attached line when metadata has no relevant field", () => {
    render(
      <SeancePanel
        tombstone={stone({ resource_type: "EC2::Volume", metadata: {} })}
        triggerEl={makeTrigger()}
        onClose={vi.fn()}
      />,
    );
    expect(screen.queryByText(/It still reserves/)).toBeNull();
  });
});
