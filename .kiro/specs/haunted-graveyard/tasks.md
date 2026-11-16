# Tasks — Haunted Graveyard

Version: 0.1 (awaiting approval)

Order: **pure logic + tests → UI → share-card canvas + exorcism animation → About.tsx fix → STATUS.md → manual verification**. Each task is one local commit with a conventional message. No push. As each task completes, tick its checkbox and update this file.

Each task lists **Satisfies** (requirement IDs) and **Verify** (how to confirm it).

---

## M1 — Pure logic (with tests)

### T1 — Haunting Score + Label pure functions
- [x] T1
- **Do:** Add `web/src/utils/hauntingScore.ts` exporting `HauntingScoreInput`, `hauntingScore(input): number` and `hauntingLabel(score): string` per the documented formula (cost min 60, volume min 25, security min 15; clamp 0–100; bands Peaceful/Restless/Haunted/Cursed). Pure, deterministic, no report mutation.
- **Files:** `web/src/utils/hauntingScore.ts`, `web/src/utils/hauntingScore.test.ts`
- **Satisfies:** AC-HG-003-1, AC-HG-003-2, AC-HG-003-3, AC-HG-003-4, AC-HG-003-6, AC-HG-003-7
- **Verify:** `cd web && npx vitest run src/utils/hauntingScore.test.ts` — cases: 0/0/0→0; demo (18/$202.15/5)→53; caps (cost 600+, volume 25+, security 3+); label boundaries 20/21/45/46/70/71/100.
- **Commit:** `feat(web): add Haunting Score and label pure functions`

### T2 — Séance story templates
- [x] T2
- **Do:** Add `web/src/utils/story.ts` exporting `Story` and `buildStory(t, now = new Date())`. One attached-line template per detector resource type + a generic fallback; age line as whole months from `created_at`/`detected_at`; cost line with "(estimated)"; attached line only when the metadata field exists, else null. All values consumed as plain text (React escapes on render).
- **Files:** `web/src/utils/story.ts`, `web/src/utils/story.test.ts`
- **Satisfies:** AC-HG-001-3, AC-HG-001-4, AC-HG-001-5, AC-HG-001-7, AC-HG-001-8
- **Verify:** `npx vitest run src/utils/story.test.ts` — one per detector type + fallback; age via a fixed `now`; `created_at` null falls back to `detected_at`; 0-months line; `attachedLine` uses metadata; null metadata → null line.
- **Commit:** `feat(web): add Séance story templates`

### T3 — Share-card data builder
- [x] T3
- **Do:** Add `web/src/utils/shareCard.ts` exporting `ShareCardData` and `buildShareCardData(report)`. Returns `{ score, label, totalCost, topNames[], empty }`; `topNames` ≤3 sorted by cost desc, using `resource_name` if present else a short type label (never an identifier). Pure.
- **Files:** `web/src/utils/shareCard.ts`, `web/src/utils/shareCard.test.ts`
- **Satisfies:** AC-HG-004-2, AC-HG-004-3, AC-HG-004-5
- **Verify:** `npx vitest run src/utils/shareCard.test.ts` — topNames sorted; ≤3; empty→sentinel; **assert output contains no `account_id`/`resource_id`/IP/key/ARN strings**.
- **Commit:** `feat(web): add share-card data builder`

---

## M2 — UI

### T4 — Exorcism store slice + CopyButton onCopied (foundation)
- [x] T4
- **Do:** Add `exorcisedResourceId`/`exorcismNonce`/`exorcise(id)` to `web/src/store/reportStore.ts`. Add an optional `onCopied?: () => void` to `web/src/components/CopyButton.tsx` (called after a successful copy; existing callers unaffected). No new dependency.
- **Files:** `web/src/store/reportStore.ts`, `web/src/components/CopyButton.tsx`
- **Satisfies:** AC-HG-005-1, AC-HG-005-3, AC-HG-005-5 (trigger mechanism), AC-HG-008-5
- **Verify:** `npx vitest run` — all existing tests still pass (additive change); `npm run build` compiles.
- **Commit:** `feat(web): add exorcism trigger store slice and CopyButton callback`

### T5 — Séance panel component
- [x] T5
- **Do:** Add `web/src/components/SeancePanel.tsx`: `role="dialog"`, `aria-modal="true"`, `aria-labelledby`; renders the story parts (from T2); "Copy cleanup command" CopyButton with `text={t.exorcism_cli}` and `onCopied={() => exorcise(t.resource_id)}`; Close button. Focus management: focus Close on open, Tab trap within, Escape → `onClose()`, return focus to the triggering element on close. Side sheet ≥768px / bottom sheet below (CSS).
- **Files:** `web/src/components/SeancePanel.tsx`, `web/src/components/SeancePanel.test.tsx`, `web/src/styles.css` (panel styles)
- **Satisfies:** AC-HG-001-1, AC-HG-001-2, AC-HG-001-6, AC-HG-006-1, AC-HG-006-3, AC-HG-006-4, AC-HG-006-5
- **Verify:** `npx vitest run src/components/SeancePanel.test.tsx` — renders story parts; `role=dialog`+`aria-modal`; Escape closes; Close returns focus; copy button calls `exorcise`.
- **Commit:** `feat(web): add Séance panel`

### T6 — Tombstone click/Enter + Graveyard panel wiring
- [x] T6
- **Do:** `TombstoneShape`: add `role="button"`, click + Enter/Space → `onOpen(triggerEl)`. `Graveyard`: hold selected-tombstone local state, render `SeancePanel` when set, pass the triggering element. Keep the existing hover epitaph.
- **Files:** `web/src/components/TombstoneShape.tsx`, `web/src/views/Graveyard.tsx`
- **Satisfies:** AC-HG-001-1, AC-HG-006-2
- **Verify:** `npx vitest run` — existing tests pass; `npm run build` compiles.
- **Commit:** `feat(web): open Séance panel from tombstones`

### T7 — Header Haunting Score + "How is this calculated?"
- [x] T7
- **Do:** Render the Haunting Score and label in `HeadlineBar` (non-colour text label always shown) using T1. Add `web/src/components/HowScoreWorks.tsx` (native `<button aria-expanded>` toggling a labelled region; text states the three inputs and that it is a heuristic, not an AWS metric; waste figure labelled "estimated"). Place beside the score.
- **Files:** `web/src/components/HeadlineBar.tsx`, `web/src/components/HowScoreWorks.tsx`, `web/src/styles.css`
- **Satisfies:** AC-HG-003-5, AC-HG-003-8, AC-HG-003-9, AC-HG-006-4
- **Verify:** `npx vitest run` — existing tests pass; `npm run build` compiles; score shown for the demo report (53 / Haunted).
- **Commit:** `feat(web): show Haunting Score with explanation in header`

### T8 — Ambient life (ghosts, candles, fog)
- [x] T8
- **Do:** `TombstoneShape`: optional `floating` prop → render a small inline-SVG ghost above the stone; render a small CSS candle at the base (staggered flicker). `Graveyard`: set `floating` for the top-3 by cost; extend the existing fog layer. All animations under `@media (prefers-reduced-motion: no-preference)`.
- **Files:** `web/src/components/TombstoneShape.tsx`, `web/src/views/Graveyard.tsx`, `web/src/styles.css`
- **Satisfies:** AC-HG-002-1, AC-HG-002-2, AC-HG-002-3, AC-HG-002-4, AC-HG-002-5, AC-HG-007-2
- **Verify:** `npx vitest run` — existing tests pass; `npm run build` compiles; reduced-motion rules present in CSS.
- **Commit:** `feat(web): add ambient ghosts, candles and fog`

---

## M3 — Share-card canvas + exorcism animation

### T9 — Share-card canvas component
- [x] T9
- **Do:** Add `web/src/components/ShareCard.tsx`: "Share my graveyard" button; on click draw score/label, total waste "(estimated)", and top-3 names onto an offscreen `<canvas>` (system `sans-serif` font), then `toBlob(png)` → client-side download via a temporary blob URL (revoked after). If Canvas/`toBlob` unavailable, disable the button with a text explanation. Use only `buildShareCardData` (T3) for content; never read identifiers. Render the button in the Graveyard view.
- **Files:** `web/src/components/ShareCard.tsx`, `web/src/views/Graveyard.tsx`, `web/src/styles.css`
- **Satisfies:** AC-HG-004-1, AC-HG-004-4, AC-HG-004-6, AC-HG-009-4
- **Verify:** `npx vitest run src/utils/shareCard.test.ts` (data layer); `npm run build` compiles. **Drawing path is verified manually (T13)** — jsdom cannot render canvas.
- **Commit:** `feat(web): add share-card PNG export`

### T10 — Exorcism vanishing animation
- [x] T10
- **Do:** `TombstoneShape`: subscribe to `exorcisedResourceId`/`exorcismNonce`; when matching `t.resource_id`, set a short `vanishing` state → `tombstone--vanishing` class (CSS `ghost-vanish`). `Exorcism`: render a small inline ghost glyph per card and subscribe likewise. Reduced-motion guard in JS + CSS. Wire the Exorcism copy buttons to `onCopied={() => exorcise(t.resource_id)}`.
- **Files:** `web/src/components/TombstoneShape.tsx`, `web/src/views/Exorcism.tsx`, `web/src/styles.css`
- **Satisfies:** AC-HG-005-1, AC-HG-005-2, AC-HG-005-4, AC-HG-005-5
- **Verify:** `npx vitest run` — existing tests pass; `npm run build` compiles. **Animation is verified manually (T13)** — CSS animation not assertable in jsdom.
- **Commit:** `feat(web): add exorcism vanishing animation`

---

## M4 — Bug fix + docs

### T11 — Fix About.tsx GitHub link
- [x] T11
- **Do:** In `web/src/views/About.tsx`, change `https://github.com/madhura/graveyard-shift` → `https://github.com/mmadhura1014/graveyard-shift`.
- **Files:** `web/src/views/About.tsx`
- **Satisfies:** AC-HG-010-1
- **Verify:** `grep -n "github.com/madhura/graveyard-shift" web/src/views/About.tsx` returns nothing; `grep -n "mmadhura1014" web/src/views/About.tsx` returns the new URL.
- **Commit:** `fix(web): correct GitHub link in About`

### T12 — STATUS.md entry + final quality gate
- [ ] T12
- **Do:** Create/append `STATUS.md` with a "Kiro CLI" heading and a short entry recording the credits used for this spec. Run the full gate: `npx vitest run` (existing 46 + new tests), `npm run build`, `npm run lint` (oxlint). Tick all completed task boxes in `tasks.md` (except T13).
- **Files:** `STATUS.md`, `.kiro/specs/haunted-graveyard/tasks.md`
- **Satisfies:** AC-HG-011-2, AC-HG-011-3, AC-HG-008-1, AC-HG-008-3, AC-HG-008-4
- **Verify:** `cd web && npx vitest run && npm run build && npm run lint` all pass; `STATUS.md` exists with a "Kiro CLI" section.
- **Commit:** `docs: add Kiro CLI status entry and finalise haunted-graveyard tasks`

---

## M5 — Manual verification (do NOT tick off — for a human in a real browser)

### T13 — Manual browser verification
- [ ] T13
- **Do:** A human runs `cd web && npm run dev` against the bundled demo report and checks each of the following in a real browser. Do not tick this off; report results separately.
- **Satisfies:** AC-HG-007-1, AC-HG-007-2, AC-HG-006-1, AC-HG-004-1, AC-HG-005-2, AC-HG-009-4
- **Checklist:**
  1. **Canvas PNG output:** click "Share my graveyard"; a PNG downloads; open it and confirm it shows the score, label, total waste with "(estimated)", and top-3 names — and contains **no account IDs, resource IDs, keys, IPs, or ARNs**.
  2. **Reduced-motion fallback:** in devtools, emulate `prefers-reduced-motion: reduce`; confirm ghosts/candles/fog are static, the scene is fully usable, clicking "Copy cleanup command" still copies and the vanishing animation does **not** play.
  3. **390px layout:** set viewport to 390×844; confirm no horizontal scroll, the Séance panel opens as a bottom sheet, the header score and Share button fit and wrap correctly.
  4. **Focus return after panel close:** tab to a tombstone, press Enter to open the panel, press Escape; confirm focus returns to the same tombstone (verify with a visible focus ring). Repeat with the Close button.
  5. **Header score:** the demo report shows "53 — Haunted" with the "How is this calculated?" button expanding to the heuristic explanation (waste labelled "estimated").
  6. **Exorcism animation (Graveyard):** open a tombstone's Séance panel, click "Copy cleanup command"; confirm the matching tombstone plays the vanishing animation.
  7. **Exorcism animation (Exorcism view):** on the Exorcism route, click a card's copy button; confirm that card's inline ghost plays the vanishing animation.
- **Verify:** human confirms each item; anything not confirmable is reported as "could not verify".
