import { describe, it, expect } from "vitest";
import { buildStory } from "./story";
import type { Tombstone } from "../types/report";

// A fixed "now" so age math is deterministic. created_at is 18 months earlier.
const NOW = new Date("2025-07-01T10:00:00Z");
const EIGHTEEN_MONTHS_AGO = "2023-12-29T10:00:00Z"; // ~549 days before NOW

function base(overrides: Partial<Tombstone>): Tombstone {
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
    created_at: EIGHTEEN_MONTHS_AGO,
    estimated_monthly_cost: 10,
    metadata: {},
    exorcism_cli: "aws ec2 delete-volume --volume-id res-1 --dry-run",
    exorcism_tf: "",
    ...overrides,
  };
}

describe("buildStory — shared parts", () => {
  it("computes the age in whole months from created_at", () => {
    const s = buildStory(base({}), NOW);
    expect(s.ageLine).toBe("Died 18 months ago.");
  });

  it("falls back to detected_at when created_at is null", () => {
    const t = base({ created_at: null, detected_at: "2025-06-15T10:00:00Z" });
    const s = buildStory(t, NOW);
    expect(s.ageLine).toBe("Died less than a month ago.");
  });

  it("says 'Died less than a month ago.' for a 0-month age", () => {
    const t = base({ created_at: "2025-06-20T10:00:00Z", detected_at: "2025-06-20T10:00:00Z" });
    expect(buildStory(t, NOW).ageLine).toBe("Died less than a month ago.");
  });

  it("handles an unparseable date without throwing", () => {
    const t = base({ created_at: "not-a-date", detected_at: "also-bad" });
    expect(buildStory(t, NOW).ageLine).toBe("Its death date is lost to the fog.");
  });

  it("formats a positive cost as estimated", () => {
    expect(buildStory(base({ estimated_monthly_cost: 40 })).costLine).toBe(
      "Still costs you $40.00/month. (estimated)",
    );
  });

  it("says 'No direct cost, but still lurking.' for zero cost", () => {
    expect(buildStory(base({ estimated_monthly_cost: 0 })).costLine).toBe(
      "No direct cost, but still lurking.",
    );
  });

  it("includes the cause of death", () => {
    expect(buildStory(base({ cause: "orphaned" })).causeLine).toBe("Cause of death: orphaned.");
  });

  it("never mutates the tombstone", () => {
    const t = base({});
    const snapshot = JSON.parse(JSON.stringify(t));
    buildStory(t, NOW);
    expect(t).toEqual(snapshot);
  });
});

describe("buildStory — attached line per detector type", () => {
  it("EC2::Volume uses size_gib + volume_type", () => {
    const s = buildStory(base({ resource_type: "EC2::Volume", metadata: { size_gib: 100, volume_type: "gp2" } }), NOW);
    expect(s.attachedLine).toBe("It still reserves 100 GiB of gp2 storage.");
  });

  it("EC2::Snapshot uses size_gib", () => {
    const s = buildStory(base({ resource_type: "EC2::Snapshot", metadata: { size_gib: 80 } }), NOW);
    expect(s.attachedLine).toBe("It keeps a 80 GiB snapshot of a volume that no longer exists.");
  });

  it("EC2::EIP uses public_ip", () => {
    const s = buildStory(base({ resource_type: "EC2::EIP", metadata: { public_ip: "203.0.113.10" } }), NOW);
    expect(s.attachedLine).toBe("It still holds the public IP 203.0.113.10, attached to nothing.");
  });

  it("ELB::LoadBalancer uses dns_name", () => {
    const s = buildStory(base({ resource_type: "ELB::LoadBalancer", metadata: { dns_name: "ghost.elb.amazonaws.com" } }), NOW);
    expect(s.attachedLine).toBe("It still answers on ghost.elb.amazonaws.com with no live targets.");
  });

  it("EC2::NatGateway uses vpc_id", () => {
    const s = buildStory(base({ resource_type: "EC2::NatGateway", metadata: { vpc_id: "vpc-1" } }), NOW);
    expect(s.attachedLine).toBe("It still sits in vpc-1, routing nothing.");
  });

  it("EC2::Instance uses ebs_size_gib", () => {
    const s = buildStory(base({ resource_type: "EC2::Instance", metadata: { ebs_size_gib: 150 } }), NOW);
    expect(s.attachedLine).toBe("It still holds 150 GiB of attached EBS.");
  });

  it("IAM::AccessKey uses username and never shows the key id", () => {
    const s = buildStory(base({ resource_type: "IAM::AccessKey", metadata: { username: "alice", key_id: "AKIAEXAMPLE" } }), NOW);
    expect(s.attachedLine).toBe("An access key for user 'alice' still lingers.");
    expect(s.attachedLine).not.toContain("AKIA");
  });

  it("EC2::SecurityGroup uses vpc_id", () => {
    const s = buildStory(base({ resource_type: "EC2::SecurityGroup", metadata: { vpc_id: "vpc-9", group_name: "orphan-sg" } }), NOW);
    expect(s.attachedLine).toBe("It still guards vpc-9 while attached to nothing.");
  });

  it("CWLogs::LogGroup uses stored_bytes", () => {
    const s = buildStory(base({ resource_type: "CWLogs::LogGroup", metadata: { stored_bytes: 52428800 } }), NOW);
    expect(s.attachedLine).toBe("It still hoards 52428800 bytes of logs with no retention.");
  });

  it("returns null attachedLine when the relevant metadata is missing", () => {
    const s = buildStory(base({ resource_type: "EC2::Volume", metadata: {} }), NOW);
    expect(s.attachedLine).toBeNull();
  });
});

describe("buildStory — fallback for unknown types", () => {
  it("returns a generic attachedLine (null) and a generic flavor line", () => {
    const s = buildStory(base({ resource_type: "S3::Bucket" }), NOW);
    expect(s.attachedLine).toBeNull();
    expect(s.flavorLine).toBe("Something the graveyard has not classified yet.");
  });

  it("produces a non-empty flavor line for every known type", () => {
    const types = [
      "EC2::Volume", "EC2::Snapshot", "EC2::EIP", "ELB::LoadBalancer",
      "EC2::NatGateway", "EC2::Instance", "IAM::AccessKey",
      "EC2::SecurityGroup", "CWLogs::LogGroup",
    ];
    for (const rt of types) {
      const s = buildStory(base({ resource_type: rt }), NOW);
      expect(s.flavorLine.length).toBeGreaterThan(0);
    }
  });
});
