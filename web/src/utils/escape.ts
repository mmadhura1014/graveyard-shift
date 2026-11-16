/**
 * Escape a value for safe text rendering.
 * React's JSX escapes by default — this helper exists for cases where
 * we build strings outside JSX (e.g. aria-labels, shell script assembly).
 * dangerouslySetInnerHTML is never used in this app.
 */
export function escapeHtml(value: string): string {
  return value
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

/** Safe display name: resource_name if present, otherwise resource_id. */
export function displayName(name: string | null, id: string): string {
  return name && name.trim() ? name.trim() : id;
}
