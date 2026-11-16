/**
 * Format a numeric monthly cost as a display string.
 * Always labelled "estimated" per the honesty rules.
 */
export function formatCost(cost: number): string {
  if (cost === 0) return "$0.00/mo (estimated)";
  return `$${cost.toFixed(2)}/mo (estimated)`;
}

export function formatCostShort(cost: number): string {
  if (cost === 0) return "–";
  return `$${cost.toFixed(2)}/mo`;
}
