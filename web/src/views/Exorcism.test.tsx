import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { Exorcism } from "./Exorcism";
import type { Report } from "../types/report";

const report: Report = {
  schema_version: "1.0",
  generated_at: "2025-07-01T10:00:00Z",
  demo: true,
  account_id: "111122223333",
  regions_scanned: ["us-east-1"],
  scan_duration_seconds: 0.5,
  summary: {
    total_tombstones: 2,
    estimated_monthly_cost: 13.65,
    undead_credentials_count: 0,
    by_severity: { harmless: 0, wasteful: 2, risky: 0 },
    by_type: { "EC2::Volume": 1, "EC2::EIP": 1 },
  },
  tombstones: [
    {
      id: "uuid-1",
      resource_id: "vol-0abc1234",
      resource_name: "old-volume",
      resource_type: "EC2::Volume",
      region: "us-east-1",
      account_id: "111122223333",
      cause: "abandoned",
      severity: "wasteful",
      detected_at: "2025-07-01T10:00:00Z",
      created_at: "2025-01-01T00:00:00Z",
      estimated_monthly_cost: 10,
      metadata: {},
      exorcism_cli: "aws ec2 delete-volume --volume-id vol-0abc1234 --region us-east-1 --dry-run",
      exorcism_tf: 'resource "aws_ebs_volume" "old_volume" {}',
    },
    {
      id: "uuid-2",
      resource_id: "eipalloc-0dead001",
      resource_name: null,
      resource_type: "EC2::EIP",
      region: "us-east-1",
      account_id: "111122223333",
      cause: "idle, costs money",
      severity: "wasteful",
      detected_at: "2025-07-01T10:00:00Z",
      created_at: null,
      estimated_monthly_cost: 3.65,
      metadata: { public_ip: "203.0.113.10" },
      exorcism_cli: "aws ec2 release-address --allocation-id eipalloc-0dead001 --region us-east-1 --dry-run",
      exorcism_tf: 'resource "aws_eip" "eipalloc_0dead001" {}',
    },
  ],
};

describe("Exorcism view", () => {
  it("shows the disclaimer", () => {
    render(<Exorcism report={report} />);
    expect(screen.getByText(/Graveyard Shift never deletes anything itself/)).toBeTruthy();
  });

  it("shows Copy All Commands button", () => {
    render(<Exorcism report={report} />);
    expect(screen.getByText(/Copy All Commands/)).toBeTruthy();
  });

  it("shows --dry-run note for commands that have it", () => {
    render(<Exorcism report={report} />);
    // The note contains "Remove" and "to execute" — check for partial text
    expect(screen.getAllByText(/Remove/).length).toBeGreaterThan(0);
  });

  it("renders a card for each tombstone", () => {
    render(<Exorcism report={report} />);
    expect(screen.getByText("old-volume")).toBeTruthy();
    expect(screen.getByText("eipalloc-0dead001")).toBeTruthy();
  });

  it("shows the CLI command for each tombstone", () => {
    render(<Exorcism report={report} />);
    expect(screen.getByText(/delete-volume.*vol-0abc1234/)).toBeTruthy();
    expect(screen.getByText(/release-address.*eipalloc-0dead001/)).toBeTruthy();
  });
});
