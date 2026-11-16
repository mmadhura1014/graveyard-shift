# Requirements — Haunted Graveyard

Version: 0.2 (approved with additions: dual exorcism-animation trigger; "How is this calculated?" explanation)

Scope: **front-end only**, all changes in `web/`. The report schema and the scanner are unchanged. Goal: make the graveyard feel alive and memorable in the first 10 seconds. Today it is a static grid of tombstones.

EARS notation key:
- **WHEN** \<trigger\> **THE SYSTEM SHALL** \<response\>
- **WHERE** \<feature exists\> **THE SYSTEM SHALL** \<behaviour\>
- **IF** \<precondition\> **THEN THE SYSTEM SHALL** \<response\>
- **THE SYSTEM SHALL** \<unconditional requirement\>

---

## 1. Séance panel

**US-HG-001** As a viewer, I want to click a tombstone and read a short, spooky story about that zombie resource, so the graveyard feels alive rather than just a chart.

- **AC-HG-001-1:** WHEN the user clicks a tombstone OR presses Enter while a tombstone is keyboard-focused THE SYSTEM SHALL open a Séance panel.
- **AC-HG-001-2:** WHERE the viewport is ≥ 768 px THE SYSTEM SHALL render the panel as a side sheet on the right; WHERE the viewport is < 768 px THE SYSTEM SHALL render it as a bottom sheet.
- **AC-HG-001-3:** THE SYSTEM SHALL build the panel story ONLY from the tombstone's own fields (resource_type, resource_name, age, estimated_monthly_cost, cause, and metadata). It SHALL NOT fetch or invent data not present on the tombstone.
- **AC-HG-001-4:** THE SYSTEM SHALL select a story template per `resource_type` and render the story in a spooky but clear tone. THE SYSTEM SHALL include at least one template for each of the nine detector resource types (EC2::Volume, EC2::Snapshot, EC2::EIP, ELB::LoadBalancer, EC2::NatGateway, EC2::Instance, IAM::AccessKey, EC2::SecurityGroup, CWLogs::LogGroup), plus a generic fallback for unknown types.
- **AC-HG-001-5:** THE SYSTEM SHALL include in the story an "age" line computed from the tombstone's `created_at` (or `detected_at` when `created_at` is null), expressed as a whole number of months (rounded down), e.g. "Died 18 months ago."
- **AC-HG-001-6:** THE SYSTEM SHALL include a "Copy cleanup command" button in the panel that copies the tombstone's `exorcism_cli` value to the clipboard, reusing the existing Exorcism plan data (no separate command source).
- **AC-HG-001-7:** WHERE `estimated_monthly_cost > 0` THE SYSTEM SHALL phrase the cost as "Still costs you $X.XX/month. (estimated)"; WHERE `estimated_monthly_cost == 0` THE SYSTEM SHALL say "No direct cost, but still lurking."
- **AC-HG-001-8:** THE SYSTEM SHALL include a "what it might still be attached to" line derived from the tombstone's `metadata` when a relevant field exists (e.g. attached EBS GiB for a stopped instance, public IP for an EIP, username for an IAM key); WHERE no relevant metadata exists THE SYSTEM SHALL omit that line rather than fabricate one.

## 2. Ambient life

**US-HG-002** As a viewer, I want slow floating ghosts, flickering candles and drifting fog so the scene feels haunted at a glance.

- **AC-HG-002-1:** THE SYSTEM SHALL render slow floating ghosts above the tombstones with the highest `estimated_monthly_cost` (at most 3 ghosts).
- **AC-HG-002-2:** THE SYSTEM SHALL render flickering candles near the base of tombstones.
- **AC-HG-002-3:** THE SYSTEM SHALL render drifting fog (the existing fog layer may be reused/extended).
- **AC-HG-002-4:** THE SYSTEM SHALL implement all ambient effects with CSS and/or lightweight inline SVG only. THE SYSTEM SHALL NOT add a new runtime dependency for these effects.
- **AC-HG-002-5:** WHERE `prefers-reduced-motion: reduce` is active THE SYSTEM SHALL disable all ambient animation while keeping the scene and all content fully visible and usable.

## 3. Haunting Score

**US-HG-003** As a viewer, I want one 0–100 score for the whole account with a label, shown in the header, so I instantly grasp how haunted my account is.

- **AC-HG-003-1:** THE SYSTEM SHALL compute a single integer Haunting Score in the range 0–100 inclusive from: total waste cost (`summary.estimated_monthly_cost`), total tombstone count (`summary.total_tombstones`), and the count of security-related tombstones.
- **AC-HG-003-2:** THE SYSTEM SHALL treat as "security-related" every tombstone whose `resource_type` is `IAM::AccessKey` OR `EC2::SecurityGroup`. (Orphaned security groups reduce attack surface; unused IAM keys are a credential risk.)
- **AC-HG-003-3:** THE SYSTEM SHALL implement the score as a single pure function `hauntingScore(input): number` taking a plain object and returning an integer, with a documented formula. The function SHALL have no side effects and SHALL be deterministic for a given input.
- **AC-HG-003-4:** THE SYSTEM SHALL map the score to a label: 0–20 `Peaceful`, 21–45 `Restless`, 46–70 `Haunted`, 71–100 `Cursed`. The mapping SHALL be a separate pure function `hauntingLabel(score): string`.
- **AC-HG-003-5:** THE SYSTEM SHALL show the score and label prominently in the header (HeadlineBar), with a non-colour signal (text label) in addition to any colour.
- **AC-HG-003-6:** THE SYSTEM SHALL label all cost-derived components as "estimated" wherever shown.
- **AC-HG-003-7:** THE SYSTEM SHALL NOT mutate the report when computing the score.
- **AC-HG-003-8:** THE SYSTEM SHALL provide a "How is this calculated?" explanation for the Haunting Score that is keyboard accessible (an expandable line or tooltip, also exposed to assistive tech) and that states the inputs (total estimated monthly waste, tombstone count, security-related tombstone count) and that the score is a heuristic, not an AWS metric.
- **AC-HG-003-9:** THE SYSTEM SHALL keep the "estimated" label on the waste figure shown within that explanation.

## 4. Share card

**US-HG-004** As a viewer, I want a "Share my graveyard" button that exports a PNG summary so I can share how haunted my account is without leaking identifiers.

- **AC-HG-004-1:** THE SYSTEM SHALL provide a "Share my graveyard" button that renders a PNG image entirely in the browser using the native Canvas API (no added dependency).
- **AC-HG-004-2:** THE PNG SHALL contain: the Haunting Score and its label, the total estimated monthly waste cost (labelled "estimated"), and the names of the top 3 tombstones by `estimated_monthly_cost`.
- **AC-HG-004-3:** THE PNG SHALL NOT contain account IDs (`account_id`), resource IDs (`resource_id`), access keys, public IPs, or ARNs. THE PNG MAY contain `resource_name` values only when they are already present in the demo data.
- **AC-HG-004-4:** WHEN the user clicks the button THE SYSTEM SHALL generate the PNG and trigger a client-side download (e.g. via a blob URL). The image SHALL never be uploaded anywhere.
- **AC-HG-004-5:** WHERE fewer than 3 tombstones exist THE SYSTEM SHALL render only those that exist. WHERE the report has zero tombstones THE SYSTEM SHALL render a card that says "Your graveyard is peaceful."
- **AC-HG-004-6:** IF the Canvas API is unavailable THE SYSTEM SHALL disable the button and show a short text explanation; it SHALL NOT throw.

## 5. Exorcism animation

**US-HG-005** As a viewer, I want a short ghost-vanishing animation when I copy a cleanup plan, so the act of exorcism feels satisfying.

- **AC-HG-005-1:** WHEN a cleanup command is copied from the Séance panel OR from a copy button in the Exorcism view THE SYSTEM SHALL trigger the exorcism animation for the matching resource.
- **AC-HG-005-2:** WHERE `prefers-reduced-motion: reduce` is active THE SYSTEM SHALL skip the animation and still complete the copy.
- **AC-HG-005-3:** THE SYSTEM SHALL match the tombstone by `resource_id`.
- **AC-HG-005-4:** THE SYSTEM SHALL NOT require any new dependency for the animation.
- **AC-HG-005-5:** WHERE the copy originates from the Séance panel THE SYSTEM SHALL play the ghost-vanishing animation on the matching tombstone in the Graveyard. WHERE the copy originates from the Exorcism view (tombstones are not mounted on that route) THE SYSTEM SHALL play the vanishing animation on a small inline ghost within the matching Exorcism card. The two paths SHALL share one animation definition and one trigger mechanism.

---

## 6. Accessibility

- **AC-HG-006-1:** THE SYSTEM SHALL make the Séance panel keyboard-reachable: the panel SHALL open on Enter from a focused tombstone, the first focusable element inside the panel SHALL receive focus on open, Tab SHALL cycle within the panel, and Escape SHALL close the panel and return focus to the triggering tombstone.
- **AC-HG-006-2:** THE SYSTEM SHALL give each tombstone a `role` and an `aria-label` that conveys name, type, cause, and cost (without relying on colour alone).
- **AC-HG-006-3:** THE SYSTEM SHALL mark the Séance panel with `role="dialog"` and `aria-modal="true"` and an accessible name, and SHALL expose its open/close state to assistive tech.
- **AC-HG-006-4:** THE SYSTEM SHALL maintain WCAG AA contrast (≥ 4.5:1 for text) across all new UI, including the Haunting Score label and the Share card preview.
- **AC-HG-006-5:** THE SYSTEM SHALL provide a visible focus indicator on all interactive elements added by this spec.

## 7. Responsive and motion constraints

- **AC-HG-007-1:** THE SYSTEM SHALL remain usable at a 390 px viewport width with no horizontal scroll, including the Séance bottom sheet.
- **AC-HG-007-2:** THE SYSTEM SHALL disable every animation introduced by this spec when `prefers-reduced-motion: reduce` is active, while keeping all content and interactions fully usable.

## 8. Quality gates

- **AC-HG-008-1:** THE SYSTEM SHALL keep all 46 existing vitest tests passing.
- **AC-HG-008-2:** THE SYSTEM SHALL add unit tests for: each story template (at least one per detector type plus the fallback), the `hauntingScore` function (boundary and typical cases), the `hauntingLabel` function (all four bands + boundaries), and the Séance panel open/close behaviour.
- **AC-HG-008-3:** `npm run build` SHALL pass (TypeScript compiles, Vite builds).
- **AC-HG-008-4:** `npm run lint` (oxlint) SHALL pass with no errors.
- **AC-HG-008-5:** THE SYSTEM SHALL NOT add any runtime or dev dependency for this spec unless the reason is stated and approved first. The Share card and animations SHALL use only the native Canvas API, CSS, and inline SVG.

## 9. Security and honesty (per .kiro/steering/security.md)

- **AC-HG-009-1:** THE SYSTEM SHALL make no real AWS calls and SHALL NOT read `~/.aws` or use credentials. The demo uses only the synthetic sample data bundled in the web app.
- **AC-HG-009-2:** THE SYSTEM SHALL treat all values from the report as untrusted and escape them when rendering; `dangerouslySetInnerHTML` SHALL NOT be used.
- **AC-HG-009-3:** THE SYSTEM SHALL label cost figures as "estimated" and the dataset as "Sample Data" where the demo report is used.
- **AC-HG-009-4:** THE SYSTEM SHALL keep the "no data leaves your browser" guarantee; the Share card and Séance panel operate fully client-side.
- **AC-HG-009-5:** No content (code, comments, commit messages, or docs produced by this spec) SHALL mention AI tools or who/what generated the code.

## 10. Bug fix

- **AC-HG-010-1:** THE SYSTEM SHALL correct the GitHub link in `web/src/views/About.tsx` from `https://github.com/madhura/graveyard-shift` to `https://github.com/mmadhura1014/graveyard-shift`.

## 11. Process

- **AC-HG-011-1:** Implementation SHALL proceed one task at a time, each in a small local commit using a conventional commit message. THE SYSTEM SHALL NOT push; the user reviews first.
- **AC-HG-011-2:** `tasks.md` checkboxes SHALL be updated as each task completes.
- **AC-HG-011-3:** A short entry SHALL be appended to `STATUS.md` under a "Kiro CLI" heading recording the credits used for this work.
- **AC-HG-011-4:** WHEN done THE SYSTEM SHALL run the vitest suite, `npm run build`, and `npm run lint` and report the real results, including anything that could not be verified.
