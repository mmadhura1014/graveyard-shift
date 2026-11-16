// Graveyard Shift — TypeScript types mirroring schema/report.schema.json

export type Severity = "harmless" | "wasteful" | "risky";

export interface Tombstone {
  id: string;
  resource_id: string;
  resource_name: string | null;
  resource_type: string;
  region: string;
  account_id: string;
  cause: string;
  severity: Severity;
  detected_at: string;
  created_at: string | null;
  estimated_monthly_cost: number;
  metadata: Record<string, unknown>;
  exorcism_cli: string;
  exorcism_tf: string;
}

export interface ReportSummary {
  total_tombstones: number;
  estimated_monthly_cost: number;
  undead_credentials_count: number;
  by_severity: { harmless: number; wasteful: number; risky: number };
  by_type: Record<string, number>;
}

export interface Report {
  schema_version: string;
  generated_at: string;
  demo: boolean;
  account_id: string;
  regions_scanned: string[];
  scan_duration_seconds: number;
  tombstones: Tombstone[];
  summary: ReportSummary;
}
