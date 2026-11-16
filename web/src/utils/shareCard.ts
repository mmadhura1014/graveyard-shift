// Share-card data builder — derives what to draw on the "Share my graveyard" PNG.
//
// Pure: no side effects, no DOM, no network. The output never contains
// account IDs, resource IDs, keys, IPs, or ARNs — only display names (or a
// short type label when a name is absent). Cost figures are estimates.

import type { Report, Tombstone } from "../types/report";
import { hauntingScore, hauntingLabel, type HauntingScoreInput } from "./hauntingScore";

export interface ShareCardData {
  /** 0–100 Haunting Score. */
  score: number;
  /** Peaceful | Restless | Haunted | Cursed. */
  label: string;
  /** Total estimated monthly waste. */
  totalCost: number;
  /** ≤ 3 display names, highest cost first. */
  topNames: string[];
  /** True when the report has no tombstones. */
  empty: boolean;
}

/** Short human label for a resource type, never an identifier. */
function shortTypeLabel(resourceType: string): string {
  const part = resourceType.split("::").pop() ?? resourceType;
  return part;
}

/** A display name for the card: resource_name if present, else the short type label. */
function displayName(t: Tombstone): string {
  if (t.resource_name && t.resource_name.trim()) return t.resource_name.trim();
  return shortTypeLabel(t.resource_type);
}

function securityCount(tombstones: Tombstone[]): number {
  return tombstones.filter(
    (t) => t.resource_type === "IAM::AccessKey" || t.resource_type === "EC2::SecurityGroup",
  ).length;
}

/**
 * Build the data for the share card. Pure and deterministic.
 * Never reads or returns identifiers (account_id, resource_id, keys, IPs, ARNs).
 */
export function buildShareCardData(report: Report): ShareCardData {
  const tombstones = report.tombstones;
  const empty = tombstones.length === 0;

  const input: HauntingScoreInput = {
    totalMonthlyCost: report.summary.estimated_monthly_cost,
    tombstoneCount: report.summary.total_tombstones,
    securityCount: securityCount(tombstones),
  };
  const score = hauntingScore(input);
  const label = hauntingLabel(score);

  const top3 = [...tombstones]
    .sort((a, b) => b.estimated_monthly_cost - a.estimated_monthly_cost)
    .slice(0, 3)
    .map(displayName);

  return {
    score,
    label,
    totalCost: report.summary.estimated_monthly_cost,
    topNames: top3,
    empty,
  };
}

/** The text shown on the card when the graveyard is empty. */
export const EMPTY_CARD_TEXT = "Your graveyard is peaceful.";
