// Séance panel — a side sheet (desktop) / bottom sheet (mobile) that tells the
// short spooky story of one zombie resource, built only from its own fields.
//
// Accessibility: role="dialog" + aria-modal, focus moves to Close on open,
// Tab is trapped inside, Escape closes, and focus returns to the triggering
// element. No new dependencies.

import { useEffect, useRef } from "react";
import type { Tombstone } from "../types/report";
import { buildStory } from "../utils/story";
import { displayName } from "../utils/escape";
import { useReportStore } from "../store/reportStore";
import { CopyButton } from "./CopyButton";

interface Props {
  tombstone: Tombstone;
  triggerEl: HTMLElement | null;
  onClose: () => void;
}

export function SeancePanel({ tombstone, triggerEl, onClose }: Props) {
  const story = buildStory(tombstone);
  const exorcise = useReportStore((s) => s.exorcise);
  const closeBtnRef = useRef<HTMLButtonElement>(null);
  const panelRef = useRef<HTMLDivElement>(null);

  // Move focus to the Close button on open.
  useEffect(() => {
    closeBtnRef.current?.focus();
  }, []);

  // Escape closes; Tab wraps within the panel.
  function onKeyDown(e: React.KeyboardEvent<HTMLDivElement>) {
    if (e.key === "Escape") {
      e.stopPropagation();
      handleClose();
      return;
    }
    if (e.key !== "Tab") return;
    const root = panelRef.current;
    if (!root) return;
    const focusables = root.querySelectorAll<HTMLElement>(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])',
    );
    if (focusables.length === 0) return;
    const first = focusables[0];
    const last = focusables[focusables.length - 1];
    const active = document.activeElement as HTMLElement | null;
    if (e.shiftKey) {
      if (active === first || !root.contains(active)) {
        e.preventDefault();
        last.focus();
      }
    } else {
      if (active === last) {
        e.preventDefault();
        first.focus();
      }
    }
  }

  function handleClose() {
    onClose();
    // Return focus to the tombstone that opened the panel.
    triggerEl?.focus();
  }

  const name = displayName(tombstone.resource_name, tombstone.resource_id);

  return (
    <>
      {/* Scrim */}
      <div className="seance-scrim" onClick={handleClose} aria-hidden="true" />

      <div
        ref={panelRef}
        className="seance-panel"
        role="dialog"
        aria-modal="true"
        aria-labelledby="seance-title"
        onKeyDown={onKeyDown}
      >
        <div className="seance-header">
          <h2 id="seance-title" className="seance-title">
            {name}
          </h2>
          <span className="seance-type">{tombstone.resource_type}</span>
          <button
            ref={closeBtnRef}
            className="seance-close"
            onClick={handleClose}
            aria-label="Close séance panel"
          >
            ✕
          </button>
        </div>

        <div className="seance-story">
          <p className="seance-line seance-age">{story.ageLine}</p>
          <p className="seance-line seance-cost">{story.costLine}</p>
          <p className="seance-line seance-cause">{story.causeLine}</p>
          {story.attachedLine && (
            <p className="seance-line seance-attached">{story.attachedLine}</p>
          )}
          <p className="seance-line seance-flavor">{story.flavorLine}</p>
        </div>

        <div className="seance-footer">
          <CopyButton
            text={tombstone.exorcism_cli}
            label="Copy cleanup command"
            onCopied={() => exorcise(tombstone.resource_id)}
          />
          <button className="seance-close-btn" onClick={handleClose}>
            Close
          </button>
        </div>
      </div>
    </>
  );
}
