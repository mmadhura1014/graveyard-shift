// Haunting Score — a 0–100 heuristic for how haunted an AWS account is.
//
// This is a heuristic, NOT an AWS metric. It combines three inputs:
//   - estimated monthly waste cost  (up to 60 points)
//   - number of tombstones          (up to 25 points)
//   - security-related tombstones    (up to 15 points)
//
// Cost figures are estimates. The functions are pure and deterministic:
// the same input always yields the same output, and the report is never mutated.

export interface HauntingScoreInput {
  /** Estimated monthly waste in USD (summary.estimated_monthly_cost). */
  totalMonthlyCost: number;
  /** Total zombie resources (summary.total_tombstones). */
  tombstoneCount: number;
  /** Security-related tombstones: IAM::AccessKey + EC2::SecurityGroup. */
  securityCount: number;
}

export const SCORE_MIN = 0;
export const SCORE_MAX = 100;

const COST_MAX = 60;
const COST_DIVISOR = 10; // $600/mo -> 60 pts
const VOLUME_MAX = 25;
const SECURITY_MAX = 15;
const SECURITY_PER_ITEM = 5; // 3 items -> 15 pts

/**
 * Compute the Haunting Score (0–100 inclusive) as an integer.
 * Pure: no side effects, deterministic.
 */
export function hauntingScore(input: HauntingScoreInput): number {
  const cost = Math.min(COST_MAX, input.totalMonthlyCost / COST_DIVISOR);
  const volume = Math.min(VOLUME_MAX, input.tombstoneCount);
  const security = Math.min(SECURITY_MAX, input.securityCount * SECURITY_PER_ITEM);
  const raw = cost + volume + security;
  const rounded = Math.round(raw);
  return clamp(rounded, SCORE_MIN, SCORE_MAX);
}

/** Map a 0–100 score to a band label. Pure. */
export function hauntingLabel(score: number): string {
  if (score <= 20) return "Peaceful";
  if (score <= 45) return "Restless";
  if (score <= 70) return "Haunted";
  return "Cursed";
}

function clamp(value: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, value));
}
