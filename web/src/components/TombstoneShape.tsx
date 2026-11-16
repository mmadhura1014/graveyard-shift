import { useState } from "react";
import type { Tombstone } from "../types/report";
import { SeverityBadge } from "./SeverityBadge";
import { displayName } from "../utils/escape";
import { formatCostShort } from "../utils/cost";

interface Props {
  tombstone: Tombstone;
  maxCost: number;
  /** Called when the stone is activated (click, Enter or Space). */
  onOpen?: (el: HTMLElement) => void;
  /** Show a floating ghost above this stone (used for the costliest few). */
  floating?: boolean;
}

const MIN_HEIGHT = 140;
const MAX_HEIGHT = 230;

/** Truncate long resource names so they fit on the stone. */
function shortName(name: string): string {
  return name.length > 11 ? `${name.slice(0, 10)}…` : name;
}

/** "EC2::Volume" -> "Volume". */
function shortType(resourceType: string): string {
  const part = resourceType.split("::").pop() ?? resourceType;
  return part.length > 12 ? `${part.slice(0, 11)}…` : part;
}

export function TombstoneShape({ tombstone: t, maxCost, onOpen, floating = false }: Props) {
  const [hovered, setHovered] = useState(false);

  const fraction = maxCost > 0 ? Math.min(t.estimated_monthly_cost / maxCost, 1) : 0;
  const height = MIN_HEIGHT + fraction * (MAX_HEIGHT - MIN_HEIGHT);
  const width = height * 0.65;

  const name = displayName(t.resource_name, t.resource_id);
  const diedDate = (t.created_at ?? t.detected_at).slice(0, 10);

  return (
    <div
      className={`tombstone tombstone--${t.severity}`}
      style={{ width, height, position: "relative" }}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      onFocus={() => setHovered(true)}
      onBlur={() => setHovered(false)}
      tabIndex={0}
      role="button"
      onClick={(e) => onOpen?.(e.currentTarget)}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          onOpen?.(e.currentTarget);
        }
      }}
      aria-label={`${name}, ${t.resource_type}, ${t.cause}, ${formatCostShort(t.estimated_monthly_cost)}`}
    >
      {floating && (
        <svg className="tomb-ghost" viewBox="0 0 24 30" width="34" height="42" aria-hidden="true" focusable="false">
          <path d="M3,28 L3,12 Q3,2 12,2 Q21,2 21,12 L21,28 L17,24 L12,28 L7,24 Z" className="ghost-body" />
          <circle cx="9" cy="12" r="1.8" className="ghost-eye" />
          <circle cx="15" cy="12" r="1.8" className="ghost-eye" />
        </svg>
      )}

      {/* SVG tombstone shape */}
      <svg
        viewBox="0 0 65 100"
        width={width}
        height={height}
        aria-hidden="true"
        className="tombstone-svg"
      >
        {/* Base slab */}
        <rect x="5" y="80" width="55" height="10" rx="2" className="tomb-base" />
        {/* Stone body */}
        <path
          d="M10,78 L10,35 Q10,10 32.5,10 Q55,10 55,35 L55,78 Z"
          className="tomb-body"
        />
        {/* R.I.P. + name + cost engraved on the stone (all text escaped by React) */}
        <text x="32.5" y="30" textAnchor="middle" className="tomb-rip">R.I.P.</text>
        <text x="32.5" y="46" textAnchor="middle" className="tomb-name">{shortName(name)}</text>
        <text x="32.5" y="58" textAnchor="middle" className="tomb-type">{shortType(t.resource_type)}</text>
        {t.estimated_monthly_cost > 0 && (
          <text x="32.5" y="70" textAnchor="middle" className="tomb-cost">
            {formatCostShort(t.estimated_monthly_cost)}
          </text>
        )}
      </svg>

      <span className="tomb-candle" aria-hidden="true" />

      {/* Severity badge below the stone (not colour-only) */}
      <div className="tombstone-badge" aria-hidden="true">
        <SeverityBadge severity={t.severity} size="sm" />
      </div>

      {/* Epitaph tooltip on hover/focus */}
      {hovered && (
        <div className="epitaph" role="tooltip">
          <p className="epitaph-name">{name}</p>
          <p className="epitaph-type">{t.resource_type}</p>
          <p className="epitaph-region">📍 {t.region}</p>
          <p className="epitaph-died">⚰ Died: {diedDate}</p>
          <p className="epitaph-cause">💀 {t.cause}</p>
          <p className="epitaph-cost">
            {t.estimated_monthly_cost > 0
              ? `💸 ${formatCostShort(t.estimated_monthly_cost)} (estimated)`
              : "No direct cost"}
          </p>
        </div>
      )}
    </div>
  );
}
