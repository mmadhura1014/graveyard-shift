import type { Severity } from "../types/report";

interface Props {
  severity: Severity;
  size?: "sm" | "md";
}

const CONFIG: Record<Severity, { label: string; icon: string; cls: string }> = {
  harmless: { label: "Harmless", icon: "☁", cls: "badge-harmless" },
  wasteful: { label: "Wasteful", icon: "💸", cls: "badge-wasteful" },
  risky:    { label: "Risky",    icon: "☠", cls: "badge-risky" },
};

export function SeverityBadge({ severity, size = "md" }: Props) {
  const { label, icon, cls } = CONFIG[severity];
  return (
    <span
      className={`severity-badge ${cls} ${size === "sm" ? "badge-sm" : ""}`}
      aria-label={`Severity: ${label}`}
    >
      <span aria-hidden="true">{icon}</span>
      <span className="badge-label">{label}</span>
    </span>
  );
}
