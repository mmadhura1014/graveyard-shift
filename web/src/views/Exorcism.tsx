import type { Report } from "../types/report";
import { CopyButton } from "../components/CopyButton";
import { SeverityBadge } from "../components/SeverityBadge";
import { displayName } from "../utils/escape";
import { formatCostShort } from "../utils/cost";

interface Props {
  report: Report;
}

export function Exorcism({ report }: Props) {
  const { tombstones } = report;

  const allCommands = tombstones
    .map((t) => `# ${displayName(t.resource_name, t.resource_id)} (${t.resource_type})\n${t.exorcism_cli}`)
    .join("\n\n");

  const shellScript = `#!/bin/bash\n# Graveyard Shift — Generated Cleanup Script\n# Review every command carefully before running.\n# Remove --dry-run flags where present to execute.\n\n${allCommands}`;

  return (
    <div className="exorcism">
      <h2 className="view-title">Exorcism</h2>
      <p className="view-subtitle">Generated cleanup plan. Run these yourself.</p>

      {/* Disclaimer */}
      <div className="exorcism-disclaimer" role="alert">
        <span aria-hidden="true">⚠️</span>{" "}
        <strong>These commands will delete resources.</strong> Review carefully before running.{" "}
        <strong>Graveyard Shift never deletes anything itself.</strong>
        {" "}Commands marked <code>--dry-run</code> are safe to preview; remove the flag to execute.
      </div>

      {/* Copy all */}
      <div className="exorcism-copy-all">
        <CopyButton text={shellScript} label="📋 Copy All Commands as Shell Script" />
      </div>

      {/* Per-tombstone cards */}
      <div className="exorcism-list">
        {tombstones.map((t) => (
          <div key={t.id} className={`exorcism-card exorcism-card--${t.severity}`}>
            <div className="exorcism-card-header">
              <span className="exorcism-name">{displayName(t.resource_name, t.resource_id)}</span>
              <SeverityBadge severity={t.severity} size="sm" />
              {t.estimated_monthly_cost > 0 && (
                <span className="exorcism-cost">{formatCostShort(t.estimated_monthly_cost)} (estimated)</span>
              )}
            </div>
            <p className="exorcism-cause">💀 {t.cause}</p>
            <p className="exorcism-rid">ID: {t.resource_id}</p>

            <div className="exorcism-block">
              <div className="exorcism-block-header">
                <span className="exorcism-block-label">AWS CLI</span>
                <CopyButton text={t.exorcism_cli} label="Copy" />
              </div>
              <pre className="exorcism-code">{t.exorcism_cli}</pre>
              {t.exorcism_cli.includes("--dry-run") && (
                <p className="exorcism-dryrun-note">
                  ℹ️ Remove <code>--dry-run</code> to execute.
                </p>
              )}
            </div>

            {t.exorcism_tf && (
              <div className="exorcism-block">
                <div className="exorcism-block-header">
                  <span className="exorcism-block-label">Terraform</span>
                  <CopyButton text={t.exorcism_tf} label="Copy" />
                </div>
                <pre className="exorcism-code">{t.exorcism_tf}</pre>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
