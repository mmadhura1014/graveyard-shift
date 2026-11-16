// Séance story builder — turns a tombstone into a short spooky story
// built ONLY from the tombstone's own fields (type, name, age, cost, cause,
// metadata). Nothing is invented; missing metadata yields null lines.
// All values are rendered as plain text by React (escaped by default).

import type { Tombstone } from "../types/report";

export interface Story {
  /** "Died 18 months ago." / "Died less than a month ago." */
  ageLine: string;
  /** "Still costs you $40.00/month. (estimated)" / "No direct cost, but still lurking." */
  costLine: string;
  /** "Cause of death: abandoned." */
  causeLine: string;
  /** Per-type line derived from metadata, or null when no relevant field exists. */
  attachedLine: string | null;
  /** One spooky per-type line. */
  flavorLine: string;
}

const MS_PER_30_DAYS = 1000 * 60 * 60 * 24 * 30;

/**
 * Build a story from a tombstone. Pass `now` to make the age deterministic in tests.
 * Pure: no side effects, never mutates the tombstone.
 */
export function buildStory(t: Tombstone, now: Date = new Date()): Story {
  return {
    ageLine: ageLine(t, now),
    costLine: costLine(t),
    causeLine: `Cause of death: ${t.cause}.`,
    attachedLine: attachedLine(t),
    flavorLine: flavorLine(t.resource_type),
  };
}

function ageLine(t: Tombstone, now: Date): string {
  const ref = t.created_at ?? t.detected_at;
  const refMs = Date.parse(ref);
  if (Number.isNaN(refMs)) return "Its death date is lost to the fog.";
  const months = Math.max(0, Math.floor((now.getTime() - refMs) / MS_PER_30_DAYS));
  return months === 0 ? "Died less than a month ago." : `Died ${months} months ago.`;
}

function costLine(t: Tombstone): string {
  if (t.estimated_monthly_cost > 0) {
    return `Still costs you $${t.estimated_monthly_cost.toFixed(2)}/month. (estimated)`;
  }
  return "No direct cost, but still lurking.";
}

function attachedLine(t: Tombstone): string | null {
  const m = t.metadata;
  switch (t.resource_type) {
    case "EC2::Volume":
      return has(m, "size_gib", "volume_type")
        ? `It still reserves ${m.size_gib} GiB of ${m.volume_type} storage.`
        : null;
    case "EC2::Snapshot":
      return has(m, "size_gib")
        ? `It keeps a ${m.size_gib} GiB snapshot of a volume that no longer exists.`
        : null;
    case "EC2::EIP":
      return has(m, "public_ip")
        ? `It still holds the public IP ${m.public_ip}, attached to nothing.`
        : null;
    case "ELB::LoadBalancer":
      return has(m, "dns_name")
        ? `It still answers on ${m.dns_name} with no live targets.`
        : null;
    case "EC2::NatGateway":
      return has(m, "vpc_id") ? `It still sits in ${m.vpc_id}, routing nothing.` : null;
    case "EC2::Instance":
      return has(m, "ebs_size_gib")
        ? `It still holds ${m.ebs_size_gib} GiB of attached EBS.`
        : null;
    case "IAM::AccessKey":
      return has(m, "username")
        ? `An access key for user '${m.username}' still lingers.`
        : null;
    case "EC2::SecurityGroup":
      return has(m, "vpc_id")
        ? `It still guards ${m.vpc_id} while attached to nothing.`
        : null;
    case "CWLogs::LogGroup":
      return has(m, "stored_bytes")
        ? `It still hoards ${m.stored_bytes} bytes of logs with no retention.`
        : null;
    default:
      return null;
  }
}

function flavorLine(resourceType: string): string {
  switch (resourceType) {
    case "EC2::Volume":
      return "A slab of storage with nothing to serve.";
    case "EC2::Snapshot":
      return "A memory of a disk that is already gone.";
    case "EC2::EIP":
      return "An address that floats, waiting for an owner who never came.";
    case "ELB::LoadBalancer":
      return "A gate left open, but no one walks through.";
    case "EC2::NatGateway":
      return "A doorway to the internet that no traffic crosses.";
    case "EC2::Instance":
      return "A host that stopped breathing but never left the ground.";
    case "IAM::AccessKey":
      return "A key still cut for a lock someone forgot to change.";
    case "EC2::SecurityGroup":
      return "A guard posted at a post that no longer exists.";
    case "CWLogs::LogGroup":
      return "A vault of whispers that no one reads.";
    default:
      return "Something the graveyard has not classified yet.";
  }
}

/** True only if every named key is present in the metadata object. */
function has(m: Record<string, unknown>, ...keys: string[]): boolean {
  return keys.every((k) => m[k] !== undefined && m[k] !== null);
}
