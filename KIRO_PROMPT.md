# Prompt to paste into kiro-cli (or Kiro IDE chat)

Run from the project root, then paste everything below the line.

---

You are my pair-builder for **Graveyard Shift**, my Kiroween 2026 hackathon entry (Costume Contest category). Read all files in `.kiro/steering/` first. They define the product, tech stack, security rules and design tone. Follow them strictly.

**Constraints:** I am solo. The hard deadline gives me about 14 days of part-time work. The project must work end to end, offline from seed data, and I must be able to show Kiro specs, steering, hooks and MCP clearly in `/.kiro` (never gitignore it).

**Work spec-driven. Do NOT write application code yet.** In this first pass:

1. Create the spec in `.kiro/specs/graveyard-shift/`:
   - `requirements.md`: user stories with EARS-style acceptance criteria covering the scanner CLI, the 9 detectors, the report schema, the web app views (Graveyard, Crypt, Exorcism, About), the demo mode, and the CDK static hosting.
   - `design.md`: architecture, data flow (AWS -> snapshot -> detectors -> report.json -> web app), the Tombstone data model, the JSON schema outline, the IAM read-only policy, the CDK stacks, error handling and logging, and a table of correctness properties suited to property-based tests (for example: detectors never mutate input; every tombstone has a non-negative cost; report validates against the schema; same snapshot gives the same report).
   - `tasks.md`: small, ordered, independently verifiable tasks grouped into milestones: M1 scanner skeleton + schema + seed data + first 3 detectors with tests; M2 remaining detectors + pricing + CLI polish; M3 web app (Graveyard, Crypt, Exorcism, About); M4 CDK hosting + IAM policy + README + one-command setup; M5 polish, demo assets, and submission docs. Each task must say how I verify it.
2. Propose (do not yet enable) these Kiro automations and write them to `.kiro/specs/graveyard-shift/automation-proposal.md`: agent hooks (for example: on save of a detector run its tests; on save of the schema regenerate types and validate the seed report; pre-commit scan for secrets and real account IDs), and which MCP servers to use (the AWS Pricing MCP server and AWS Documentation MCP server to verify pricing and API behaviour, with the exact config snippet for `.kiro/settings/mcp.json`).
3. Stop and wait for my approval of each spec file before moving to implementation. Do not invent features beyond the steering docs, and do not claim any result you haven't actually run.

When I approve, we'll execute `tasks.md` one milestone at a time, running tests after each task, and I will confirm each milestone before we continue.
