# Design — Haunted Graveyard

Version: 0.1 (awaiting approval)

Scope: **front-end only**, all changes in `web/`. The report schema and the scanner are unchanged. No new dependencies are added (confirmed in §11).

---

## 1. Architecture overview

All new code lives inside the existing Vite + React + TS SPA. The report store (Zustand) gains one small slice for the exorcism animation. Everything else is pure functions, components, and CSS.

```
Report (immutable, from store)
   │
   ├── utils/hauntingScore.ts   (pure) ──► HeadlineBar (score + label + "How?" explanation)
   ├── utils/story.ts            (pure) ──► SeancePanel (per-type spooky story)
   ├── utils/shareCard.ts        (pure) ──► ShareCard (canvas PNG, no IDs)
   │
   views/Graveyard.tsx
   ├── renders TombstoneShape[] (now clickable, with floating ghosts + candles)
   ├── owns selectedTombstone (local state) ──► SeancePanel
   └── renders ShareCard button
   │
   store/reportStore.ts
   └── exorcisedResourceId + exorcismNonce  (shared trigger)
        ▲                              ▲
   CopyButton (Séance)            CopyButton (Exorcism view)
        │                              │
        └──────── exorcise(id) ────────┘
                    │
   TombstoneShape (Graveyard)  +  inline ghost (Exorcism card)
   both subscribe to the same store flag → same CSS animation
```

Data flow is one-way and read-only: the report is never mutated. Pure utils derive display data; components render it.

---

## 2. Séance panel

### Component
`web/src/components/SeancePanel.tsx` — props: `{ tombstone: Tombstone; triggerEl: HTMLElement | null; onClose: () => void }`.

- Renders `<div role="dialog" aria-modal="true" aria-labelledby="seance-title">`.
- Title = displayName(name, resource_id) + resource_type.
- Body = story parts (from `utils/story.ts`) rendered as styled paragraphs.
- Footer = "Copy cleanup command" (CopyButton with `text={tombstone.exorcism_cli}` and `onCopied={() => exorcise(tombstone.resource_id)}`) + "Close" button.

### Triggering
`Graveyard.tsx` holds `const [selected, setSelected] = useState<{tombstone, triggerEl} | null>(null)`. `TombstoneShape` gets `onOpen={(el) => setSelected({tombstone: t, triggerEl: el})}`. Click and Enter (keydown `Enter`/`Space`) call `onOpen(currentTarget)`.

### Focus management (no dependency)
- On mount: store `document.activeElement` (the triggering tombstone, already passed as `triggerEl`); move focus to the Close button (ref).
- `onKeyDown` at panel root: `Escape` → `onClose()`. `Tab`/`Shift+Tab` → query focusable elements within the panel and wrap focus (manual trap with `querySelectorAll`).
- On close: `triggerEl?.focus()` returns focus to the tombstone.

### Placement (CSS, no JS branch)
One component; CSS `@media (min-width: 768px)` → right side sheet; below 768 px → bottom sheet. No JS width check; fully responsive by CSS.

### Story builder
`web/src/utils/story.ts` — `buildStory(t: Tombstone, now = new Date()): Story`.

```ts
interface Story {
  ageLine: string;          // "Died 18 months ago." | "Died less than a month ago."
  costLine: string;          // "Still costs you $40.00/month. (estimated)" | "No direct cost, but still lurking."
  causeLine: string;         // "Cause of death: abandoned."
  attachedLine: string | null; // per-type, from metadata; null if no relevant field
  flavorLine: string;        // one spooky per-type line
}
```

Age: `months = max(0, floor((now - (created_at ?? detected_at)) / 30 days))`. `0 → "Died less than a month ago."` else `"Died N months ago."` Deterministic via the `now` param (tests pass a fixed date).

Attached lines per type (only emitted when the metadata field exists; all values are React-escaped by default rendering):
| resource_type | metadata used | line |
|---|---|---|
| EC2::Volume | size_gib, volume_type | "It still reserves {size_gib} GiB of {volume_type} storage." |
| EC2::Snapshot | size_gib | "It keeps a {size_gib} GiB snapshot of a volume that no longer exists." |
| EC2::EIP | public_ip | "It still holds the public IP {public_ip}, attached to nothing." |
| ELB::LoadBalancer | lb_type, dns_name | "It still answers on {dns_name} with no live targets." |
| EC2::NatGateway | vpc_id | "It still sits in {vpc_id}, routing nothing." |
| EC2::Instance | ebs_size_gib, instance_type | "It still holds {ebs_size_gib} GiB of attached EBS." |
| IAM::AccessKey | username, status | "An access key for user '{username}' still lingers." (no key id shown) |
| EC2::SecurityGroup | vpc_id, group_name | "It still guards {vpc_id} while attached to nothing." |
| CWLogs::LogGroup | stored_bytes | "It still hoards {stored_bytes} bytes of logs with no retention." |
| (fallback) | — | null |

---

## 3. Ambient life

CSS + inline SVG only. No JS libs.

- **Ghosts:** `TombstoneShape` accepts `floating?: boolean`. `Graveyard` sets it for the top-3 by cost. When set, a small inline SVG ghost renders above the stone and floats via a `@keyframes float` (translateY) — disabled under reduced-motion.
- **Candles:** a small CSS candle (a thin div with a flickering `box-shadow`/`opacity` glow) at the base of each tombstone; staggered `animation-delay` per index — disabled under reduced-motion.
- **Fog:** reuse/extend the existing `.fog-layer`.

All animations wrapped in `@media (prefers-reduced-motion: no-preference)` so they never run when reduced-motion is set; the elements remain visible (ghosts/candles drawn statically).

---

## 4. Haunting Score

Two pure functions in `web/src/utils/hauntingScore.ts`. No side effects, deterministic, no report mutation.

### Inputs (plain object)
```ts
interface HauntingScoreInput {
  totalMonthlyCost: number;   // summary.estimated_monthly_cost
  tombstoneCount: number;     // summary.total_tombstones
  securityCount: number;      // count of IAM::AccessKey + EC2::SecurityGroup tombstones
}
```

### Formula (documented)
```
costComponent     = min(60, totalMonthlyCost / 10)     // $0→0, $600+→60
volumeComponent   = min(25, tombstoneCount)            // 0→0, 25+→25
securityComponent = min(15, securityCount * 5)          // 0→0, 3+→15
raw      = costComponent + volumeComponent + securityComponent   // 0..100
score    = clamp(round(raw), 0, 100)
```

### Labels
```ts
function hauntingLabel(score: number): string {
  if (score <= 20) return "Peaceful";
  if (score <= 45) return "Restless";
  if (score <= 70) return "Haunted";
  return "Cursed";
}
```
Boundaries: 20 → Peaceful, 21 → Restless, 45 → Restless, 46 → Haunted, 70 → Haunted, 71 → Cursed.

### Demo data check
18 tombstones, $202.15/mo, security = 3 IAM keys + 2 security groups = 5:
cost = 20.215, volume = 18, security = min(15, 25) = 15 → raw = 53.215 → **53 → "Haunted"**.

### "How is this calculated?" explanation
`web/src/components/HowScoreWorks.tsx` — a `<button aria-expanded>` toggling a `<div role="region" aria-live="polite">`. Text (exact):
> "The Haunting Score is a heuristic, not an AWS metric. It adds three inputs: estimated monthly waste (up to 60 pts), number of tombstones (up to 25 pts), and security-related tombstones — unused IAM keys and orphaned security groups (up to 15 pts). The waste figure is estimated."
Keyboard accessible (native button), Escape closes it. Rendered in HeadlineBar beside the score.

---

## 5. Share card

### Data builder (pure, unit-tested)
`web/src/utils/shareCard.ts` — `buildShareCardData(report): ShareCardData`:
```ts
interface ShareCardData {
  score: number;
  label: string;
  totalCost: number;          // estimated; rendered with "(estimated)"
  topNames: string[];         // ≤3, by cost desc; resource_name if present, else short type label
  empty: boolean;             // true when 0 tombstones
}
```
- Never includes `account_id`, `resource_id`, keys, IPs, or ARNs. `resource_name` used only when present; otherwise the short type (e.g. "Volume") — never an identifier.
- `empty` → the card renders "Your graveyard is peaceful."

### Rendering (canvas, not unit-tested — see §10)
`web/src/components/ShareCard.tsx` — button "Share my graveyard". On click:
1. Create offscreen `<canvas width=1080 height=640>` (not appended to DOM).
2. Draw dark background, title "My Graveyard", score + label (large), total waste "(estimated)", top-3 names list.
3. `canvas.toBlob(png)` → download via a temporary `<a download="graveyard-shift.png">` + `URL.createObjectURL`; revoke URL after.
4. If `HTMLCanvasElement`/`toBlob` unavailable → disable button, show "Sharing isn't supported in this browser."

Fonts: `ctx.font = "…px sans-serif"` (system default; no external font). Everything stays in the browser; nothing is uploaded.

---

## 6. Exorcism animation (shared mechanism)

One trigger, two mount points — this is why the dual trigger stays simple.

### Store slice (added to `reportStore.ts`)
```ts
exorcisedResourceId: string | null;
exorcismNonce: number;
exorcise: (resourceId: string) => void;   // sets id, increments nonce
```

### Shared trigger
`CopyButton` gains an optional `onCopied?: () => void`. The Séance panel and every Exorcism-view copy button pass `onCopied={() => exorcise(t.resource_id)}`. The existing clipboard logic is unchanged; this is an additive callback.

### Mount point A — Graveyard tombstone
`TombstoneShape` subscribes to `exorcisedResourceId`/`exorcismNonce`. When they match `t.resource_id` (nonce change), set local `vanishing=true` for 700 ms → adds class `tombstone--vanishing`. CSS plays `@keyframes ghost-vanish` (fade + rise). Self-clears.

### Mount point B — Exorcism card
Each `Exorcism` card renders a small inline ghost glyph. Same subscription: when its `resource_id` matches, it plays the same `ghost-vanish` animation on the glyph.

### Reduced motion
The keyframes live under `@media (prefers-reduced-motion: no-preference)`. Under reduced motion the class toggle has no visual effect; the copy still completes (satisfies AC-HG-005-2). The JS also guards: it won't set `vanishing` when `matchMedia('(prefers-reduced-motion: reduce)').matches`.

One CSS animation, one store action, two listeners. No new dependency.

---

## 7. Accessibility

- Tombstones: `role="button"`, `tabIndex={0}`, `aria-label` already conveys name/type/cause/cost; click + Enter/Space open the panel.
- Panel: `role="dialog"`, `aria-modal="true"`, `aria-labelledby`; focus trap + Escape + focus return (§2).
- Score: non-colour text label always shown; colour is supplementary.
- "How?": native `<button aria-expanded>` + labelled region; keyboard operable.
- All new interactive elements get a visible focus ring (CSS `:focus-visible`).
- Contrast ≥ 4.5:1 for all new text (verified against the existing palette tokens).

---

## 8. Responsive & motion

- 390 px: bottom sheet panel; no horizontal scroll (panel width: 100vw − padding, max 420 px; content wraps).
- All animations under `@media (prefers-reduced-motion: no-preference)`; reduced-motion shows static ghosts/candles/fog and skips the vanish animation.

---

## 9. File map

**New**
- `web/src/utils/hauntingScore.ts` + `.test.ts`
- `web/src/utils/story.ts` + `.test.ts`
- `web/src/utils/shareCard.ts` + `.test.ts`
- `web/src/components/SeancePanel.tsx` + `.test.tsx`
- `web/src/components/HowScoreWorks.tsx`
- `web/src/components/ShareCard.tsx`

**Changed**
- `web/src/components/TombstoneShape.tsx` — click/Enter open panel; floating ghost + candle; vanish subscription.
- `web/src/views/Graveyard.tsx` — selected-tombstone state; render SeancePanel; `floating` for top-3; Share button.
- `web/src/components/HeadlineBar.tsx` — Haunting Score + label + HowScoreWorks.
- `web/src/views/Exorcism.tsx` — copy buttons call `exorcise`; inline ghost glyph per card.
- `web/src/store/reportStore.ts` — `exorcisedResourceId`/`exorcismNonce`/`exorcise`.
- `web/src/components/CopyButton.tsx` — optional `onCopied` callback.
- `web/src/views/About.tsx` — fix GitHub URL → `mmadhura1014`.
- `web/src/styles.css` — panel, score, share, ambient, animation, reduced-motion rules.

**Unchanged**: schema, scanner, all detector code, report types (no field added).

---

## 10. Test plan

| Suite | Covers | Count (new) |
|---|---|---|
| `hauntingScore.test.ts` | 0/0/0→0; demo→53; caps (cost 600+, volume 25+, security 3+); label boundaries 20/21/45/46/70/71/100 | ~10 |
| `story.test.ts` | one per detector type + fallback; age via fixed `now`; `created_at` null→`detected_at`; 0-months line; `attachedLine` uses metadata; null metadata → null line | ~12 |
| `shareCard.test.ts` | topNames sorted by cost; ≤3; empty→sentinel; **no identifiers in output** (assert no `account_id`/`resource_id`/IP/key strings) | ~6 |
| `SeancePanel.test.tsx` | renders story parts; `role=dialog`+`aria-modal`; Escape closes; Close returns focus; copy button calls `exorcise` | ~6 |

Existing 46 tests must stay green.

**Cannot unit-test:** the actual canvas drawing (`ShareCard.tsx`) — jsdom does not implement canvas rendering, so `toBlob`/`toDataURL` are stubs. I test only the pure `buildShareCardData`; the drawing is verified manually in the browser (stated in the final report). CSS animations are also not asserted in jsdom; reduced-motion is covered by CSS, verified manually.

---

## 11. Dependencies

**None added.** Share card uses the native Canvas API; animations use CSS + inline SVG; clipboard reuses the existing `CopyButton`. `zustand` (already present) backs the exorcism slice. If a dependency ever seemed necessary, it would be proposed and approved before adding (per AC-HG-008-5).

---

## 12. Bug fix & process notes

- About.tsx URL: `https://github.com/madhura/graveyard-shift` → `https://github.com/mmadhura1014/graveyard-shift`.
- One task per commit, conventional messages (e.g. `feat(web): add Haunting Score`), local only, no push.
- No code/comment/commit/doc mentions AI tools or authorship.
- `tasks.md` checkboxes updated as each task completes; `STATUS.md` "Kiro CLI" entry added with credits used.
