import type { ReportSummary } from "../types/report";

interface Props {
  summary: ReportSummary;
  demo: boolean;
}

export function HeadlineBar({ summary, demo }: Props) {
  return (
    <div className="headline-bar" role="region" aria-label="Summary statistics">
      {demo && (
        <span className="sample-badge" aria-label="This is sample data, not a real scan">
          🎃 Sample Data
        </span>
      )}

      <div className="headline-stat">
        <span className="headline-number" aria-label={`${summary.total_tombstones} tombstones`}>
          {summary.total_tombstones}
        </span>
        <span className="headline-label">Tombstones</span>
      </div>

      <div className="headline-divider" aria-hidden="true" />

      <div className="headline-stat">
        <span
          className="headline-number headline-cost"
          aria-label={`Estimated monthly cost $${summary.estimated_monthly_cost.toFixed(2)}`}
        >
          ${summary.estimated_monthly_cost.toFixed(2)}/mo
        </span>
        <span className="headline-label">Estimated Haunting Cost</span>
      </div>

      <div className="headline-divider" aria-hidden="true" />

      <div className="headline-stat">
        <span
          className="headline-number headline-risky"
          aria-label={`${summary.undead_credentials_count} undead credentials`}
        >
          {summary.undead_credentials_count}
        </span>
        <span className="headline-label">Undead Credentials</span>
      </div>
    </div>
  );
}
