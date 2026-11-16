# Design and tone

- Theme: moody night-time cemetery. Dark background, fog, a moon, low-saturation palette with one accent glow per severity (green = harmless, amber = wasteful, red = risky).
- Hero screen: a graveyard scene where each zombie resource is a tombstone sized/positioned by monthly cost; hover shows epitaph (name, type, region, "died" date, cause of death, estimated monthly cost).
- Views: Graveyard (scene), Crypt (sortable table, filters by type/region/severity), Exorcism (generated cleanup plan per tombstone with copy buttons), About (how it works, read-only guarantee, IAM policy).
- Headline numbers: total tombstones, estimated monthly haunting cost, "undead credentials" count.
- Copy tone: playful but precise. The jokes live in labels and epitaphs; the data and commands stay exact and unambiguous.
- Accessibility: all information must also be available in the Crypt table; respect `prefers-reduced-motion`; colour is never the only signal; contrast >= WCAG AA on text.
- Responsive down to 390px width. No external fonts or images required at runtime (bundle assets; use only licence-clear assets).
- No third-party trademarks or copyrighted music in the app or demo video.
