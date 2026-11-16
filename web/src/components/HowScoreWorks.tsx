import { useId, useState } from "react";

/** Keyboard-accessible explanation of how the Haunting Score is calculated. */
export function HowScoreWorks() {
  const [open, setOpen] = useState(false);
  const id = useId();

  return (
    <div
      className="how-score"
      onKeyDown={(e) => {
        if (e.key === "Escape" && open) {
          e.stopPropagation();
          setOpen(false);
        }
      }}
    >
      <button
        type="button"
        className="how-score-btn"
        aria-expanded={open}
        aria-controls={id}
        onClick={() => setOpen((o) => !o)}
      >
        How is this calculated?
      </button>
      {open && (
        <div id={id} className="how-score-body" role="region" aria-label="How the Haunting Score is calculated" aria-live="polite">
          <p>
            The Haunting Score is a <strong>heuristic</strong>, not an AWS metric. It adds up
            three things: the <em>estimated</em> monthly waste (up to 60 points), the number of
            tombstones (up to 25), and the number of security-related ones, such as unused access
            keys and unattached security groups (up to 15). Higher means more haunted.
          </p>
          <p>Peaceful 0–20 · Restless 21–45 · Haunted 46–70 · Cursed 71–100</p>
        </div>
      )}
    </div>
  );
}
