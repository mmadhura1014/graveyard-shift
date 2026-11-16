# STATUS: Graveyard Shift (Kiroween 2026)

**Last updated:** 2026-11-16 | **Days to internal target (2 Dec IST):** 16 | **Days to hard deadline (5 Dec 03:30 IST):** ~18.5

## Decisions
- Category: Costume Contest (spooky polished UI). Solo.
- Idea: AWS zombie-resource scanner shown as a haunted graveyard. Read-only, never deletes.
- Stack: Python 3.12 scanner CLI, Vite+React+TS static web app, AWS CDK (TS) for S3+CloudFront, bundled seed data. No LLM, no backend.
- NO real AWS usage (only an org account exists, personal accounts get suspended). Live scan path is tested/demoed against `moto` (fake AWS). Public demo hosted on free static host (GitHub Pages/Netlify/Cloudflare Pages). CDK is an optional `cdk synth`-only stretch.
- Hosting must stay live and free until 29 Jan 2027 (judging ends). Static site keeps idle cost zero.
- Repo must be public on GitHub with OSI licence (plan: MIT) and `/.kiro` committed.
- Project must be new (created after 30 Oct 2026). Repo created 16 Nov 2026.

## Progress log (what was done in Kiro vs outside it, for the Kiro write-up)
- 2026-11-16 Kiro CLI: steering-driven spec (requirements/design/tasks/automation-proposal), scanner + 9 detectors, CLI, seed data, web skeleton + views, moto integration tests (176 py + 46 web tests pass). Kiro free credits ran out twice; switched to a second account.
- 2026-11-16 Manual (outside Kiro): steering files + KIRO_PROMPT.md; fixed `scripts/moto_demo_scan.py` (moto ignores OwnerIds=self, inflated count to 1309; now 8); redesigned Graveyard hero view (names/cost on stones, grid layout, cost-sorted). Verified with headless-Chrome screenshots.
- STILL TO DO IN KIRO (needed for Kiro-usage score): enable agent hooks, MCP config (AWS Pricing/Docs), show hooks firing.
- 2026-11-16 Kiro CLI: new spec `haunted-graveyard` (requirements, design, tasks approved step by step); implemented T1-T4 (Haunting Score, story templates, share-card data, exorcism store slice). Free credits ran out partway through T5.
- 2026-11-16 Manual (outside Kiro): finished T5-T12 from Kiro's approved tasks.md (Séance panel, tombstone click, header score + explanation, ghosts/candles, share-card PNG, exorcism animation, About link fix, mobile row spacing). 102 web tests, build and lint pass. Checked in headless Chrome over CDP: panel focus/Escape/focus-return, vanish class (absent under reduced motion), share PNG content, no horizontal scroll at 390px. T13 (human check in a real browser) still open.

## Milestones
- [ ] M0 Spec approved (requirements, design, tasks, automation proposal)
- [ ] M1 Scanner skeleton, schema, seed data, 3 detectors + tests
- [ ] M2 Remaining detectors, pricing, CLI polish
- [ ] M3 Web app (Graveyard, Crypt, Exorcism, About)
- [ ] M4 CDK hosting, IAM policy, README, one-command setup
- [ ] M5 Polish, demo video, screenshots, Devpost write-up

## Target schedule
- 16-18 Nov: M0, M1
- 19-22 Nov: M2, start M3
- 23-27 Nov: M3, M4 (deploy to your AWS account)
- 28-30 Nov: M5 polish, record video
- 1 Dec: buffer. (Credits already not needed; Kiro works.)
- 2 Dec IST: SUBMIT. 4 Dec 2 PM PT is the hard cutoff, no extensions.

## Open items for you
- Create a **public GitHub repo** (personal account) and tell me when it exists.
- Confirm form character limits on the live Devpost form before I write final copy.
- Register on Devpost yourself.

## Not yet verified
- Devpost form field character limits.
- Exact Rules page wording (Devpost blocked my fetch; summaries are third-party).
