import type { Report, Severity } from "../types/report";
import { useFilter, type SortKey } from "../hooks/useFilter";
import { SeverityBadge } from "../components/SeverityBadge";
import { displayName } from "../utils/escape";
import { formatCostShort } from "../utils/cost";

interface Props {
  report: Report;
}

const COLUMNS: { key: SortKey; label: string }[] = [
  { key: "resource_name",           label: "Resource Name" },
  { key: "resource_type",           label: "Type" },
  { key: "region",                  label: "Region" },
  { key: "severity",                label: "Severity" },
  { key: "cause",                   label: "Cause of Death" },
  { key: "detected_at",             label: "Died Date" },
  { key: "estimated_monthly_cost",  label: "Est. Monthly Cost" },
];

const SEVERITIES: Severity[] = ["harmless", "wasteful", "risky"];

export function Crypt({ report }: Props) {
  const {
    filtered, filters, sortKey, sortDir,
    allTypes, allRegions,
    toggleSort, toggleFilter, clearFilters, count,
  } = useFilter(report.tombstones);

  return (
    <div className="crypt">
      <h2 className="view-title">The Crypt</h2>
      <p className="view-subtitle">Every zombie, sorted and exposed.</p>

      {/* Filters */}
      <div className="crypt-filters" role="group" aria-label="Filter tombstones">
        <div className="filter-group">
          <span className="filter-label">Severity</span>
          <div className="filter-chips">
            {SEVERITIES.map((s) => (
              <button
                key={s}
                className={`filter-chip filter-chip--${s} ${filters.severities.includes(s) ? "active" : ""}`}
                onClick={() => toggleFilter("severities", s)}
                aria-pressed={filters.severities.includes(s)}
              >
                <SeverityBadge severity={s} size="sm" />
              </button>
            ))}
          </div>
        </div>

        <div className="filter-group">
          <span className="filter-label">Type</span>
          <div className="filter-chips">
            {allTypes.map((type) => (
              <button
                key={type}
                className={`filter-chip ${filters.types.includes(type) ? "active" : ""}`}
                onClick={() => toggleFilter("types", type)}
                aria-pressed={filters.types.includes(type)}
              >
                {type}
              </button>
            ))}
          </div>
        </div>

        <div className="filter-group">
          <span className="filter-label">Region</span>
          <div className="filter-chips">
            {allRegions.map((r) => (
              <button
                key={r}
                className={`filter-chip ${filters.regions.includes(r) ? "active" : ""}`}
                onClick={() => toggleFilter("regions", r)}
                aria-pressed={filters.regions.includes(r)}
              >
                {r}
              </button>
            ))}
          </div>
        </div>

        {(filters.severities.length > 0 || filters.types.length > 0 || filters.regions.length > 0) && (
          <button className="filter-clear" onClick={clearFilters}>
            Clear filters
          </button>
        )}
      </div>

      <p className="crypt-count" aria-live="polite">
        Showing {count} of {report.tombstones.length} tombstone{report.tombstones.length !== 1 ? "s" : ""}
      </p>

      {/* Table */}
      <div className="crypt-table-wrapper" role="region" aria-label="Tombstones table">
        <table className="crypt-table" aria-rowcount={count}>
          <thead>
            <tr>
              {COLUMNS.map(({ key, label }) => (
                <th
                  key={key}
                  scope="col"
                  className={`crypt-th ${sortKey === key ? "sort-active" : ""}`}
                  onClick={() => toggleSort(key)}
                  aria-sort={
                    sortKey === key
                      ? sortDir === "asc" ? "ascending" : "descending"
                      : "none"
                  }
                  style={{ cursor: "pointer" }}
                >
                  {label}
                  {sortKey === key && (
                    <span aria-hidden="true">{sortDir === "asc" ? " ↑" : " ↓"}</span>
                  )}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {filtered.map((t) => (
              <tr key={t.id} className={`crypt-row crypt-row--${t.severity}`}>
                <td className="crypt-td" title={t.resource_id}>
                  <span className="resource-name">{displayName(t.resource_name, t.resource_id)}</span>
                  <span className="resource-id">{t.resource_id}</span>
                </td>
                <td className="crypt-td">{t.resource_type}</td>
                <td className="crypt-td">{t.region}</td>
                <td className="crypt-td">
                  <SeverityBadge severity={t.severity} />
                </td>
                <td className="crypt-td">{t.cause}</td>
                <td className="crypt-td">{(t.created_at ?? t.detected_at).slice(0, 10)}</td>
                <td className="crypt-td crypt-cost">
                  {t.estimated_monthly_cost > 0 ? formatCostShort(t.estimated_monthly_cost) : "–"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {count === 0 && (
          <p className="crypt-empty">No tombstones match the current filters.</p>
        )}
      </div>
    </div>
  );
}
