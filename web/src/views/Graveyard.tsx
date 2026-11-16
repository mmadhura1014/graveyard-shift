import { useState } from "react";
import type { Report } from "../types/report";
import { TombstoneShape } from "../components/TombstoneShape";
import { SeancePanel } from "../components/SeancePanel";
import type { Tombstone } from "../types/report";

interface Props {
  report: Report;
}

export function Graveyard({ report }: Props) {
  // Most expensive ghosts stand first (top-left), sorted without mutating the report.
  const [selected, setSelected] = useState<{ t: Tombstone; el: HTMLElement | null } | null>(null);
  const tombstones = [...report.tombstones].sort(
    (a, b) => b.estimated_monthly_cost - a.estimated_monthly_cost,
  );
  const floatingIds = new Set(tombstones.filter((t) => t.estimated_monthly_cost > 0).slice(0, 3).map((t) => t.id));
  const maxCost = Math.max(...tombstones.map((t) => t.estimated_monthly_cost), 1);

  return (
    <div className="graveyard" aria-label="Graveyard scene">
      {/* Sky layer */}
      <div className="graveyard-sky" aria-hidden="true">
        <div className="moon" aria-hidden="true" />
        <div className="stars" aria-hidden="true">
          {Array.from({ length: 30 }).map((_, i) => (
            <span key={i} className="star" style={{
              left: `${(i * 37 + 11) % 100}%`,
              top: `${(i * 23 + 7) % 60}%`,
              animationDelay: `${(i * 0.3) % 3}s`,
            }} />
          ))}
        </div>
      </div>

      {/* Fog layer */}
      <div className="fog-layer" aria-hidden="true">
        <div className="fog fog-1" />
        <div className="fog fog-2" />
      </div>

      {/* Tombstones */}
      <div className="tombstone-field" role="list" aria-label={`${tombstones.length} zombie resources`}>
        {tombstones.map((t) => (
          <div key={t.id} role="listitem">
            <TombstoneShape tombstone={t} maxCost={maxCost} onOpen={(el) => setSelected({ t, el })} floating={floatingIds.has(t.id)} />
          </div>
        ))}
      </div>

      {selected && (
        <SeancePanel
          tombstone={selected.t}
          triggerEl={selected.el}
          onClose={() => setSelected(null)}
        />
      )}

      {/* Ground line */}
      <div className="graveyard-ground" aria-hidden="true" />

      {tombstones.length === 0 && (
        <div className="graveyard-empty">
          <p>🎉 No zombies found. Your account is clean!</p>
        </div>
      )}
    </div>
  );
}
