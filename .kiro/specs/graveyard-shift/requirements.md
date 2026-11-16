# Requirements — Graveyard Shift

Version: 0.1 (pre-implementation, awaiting approval)

EARS notation key:
- **WHEN** \<trigger\> **THE SYSTEM SHALL** \<response\>
- **WHERE** \<feature exists\> **THE SYSTEM SHALL** \<behaviour\>
- **IF** \<precondition\> **THEN THE SYSTEM SHALL** \<response\>
- **THE SYSTEM SHALL** \<unconditional requirement\>

---

## 1. Scanner CLI

### 1.1 Invocation

**US-001** As an SRE, I want to run `graveyard scan --profile <name> --regions <list> --out report.json` so that I get a report of zombie resources in my AWS account without any resource being modified.

- AC-001-1: WHEN the command completes successfully THE SYSTEM SHALL write a JSON file at the path given by `--out` that validates against `schema/report.schema.json`.
- AC-001-2: THE SYSTEM SHALL exit with code 0 on success, 1 on a configuration or credential error, 2 on a partial failure where some regions errored.
- AC-001-3: WHERE `--regions` is omitted THE SYSTEM SHALL scan all regions returned by `ec2:DescribeRegions` that are enabled for the account.
- AC-001-4: WHERE `--out` is omitted THE SYSTEM SHALL write `report.json` in the current working directory.
- AC-001-5: THE SYSTEM SHALL never call any mutating AWS API (no Create*, Delete*, Put*, Update*, Terminate*, etc.).

### 1.2 Demo mode

**US-002** As a user without AWS credentials, I want `graveyard scan --demo` to produce a valid report from bundled seed data so I can explore the tool offline.

- AC-002-1: WHEN `--demo` is passed THE SYSTEM SHALL read `seed/snapshot.json`, run all detectors against it, and write the report without making any AWS API calls.
- AC-002-2: THE SYSTEM SHALL label the demo report with `"demo": true` in its metadata block.
- AC-002-3: IF a `--profile` or `--regions` flag is also passed with `--demo` THE SYSTEM SHALL emit a warning and ignore those flags.
- AC-002-4: `make demo` SHALL run demo mode and open (or print the path to) the resulting report.

### 1.3 Credentials and safety

- AC-003-1: THE SYSTEM SHALL load credentials only from the standard AWS credential chain (env vars, `~/.aws/credentials`, instance profile, etc.) or the named profile given by `--profile`.
- AC-003-2: THE SYSTEM SHALL never log credential values, secret access keys, or full resource ARNs at INFO level or below.
- AC-003-3: THE SYSTEM SHALL never hard-code account IDs, access keys, or ARNs.

### 1.4 Thresholds and configuration

**US-003** As an operator, I want all detection thresholds in one config file so I can tune them without touching detector code.

- AC-004-1: THE SYSTEM SHALL read thresholds from `scanner/config.py` (Python dict with documented defaults).
- AC-004-2: WHERE `--config <path>` is supplied THE SYSTEM SHALL merge the TOML file at that path over the defaults.
- AC-004-3: THE SYSTEM SHALL document every threshold key and default value in `README.md`.

---

## 2. Detectors

Each detector is a pure function `detect(snapshot: Snapshot) -> list[Tombstone]`. All nine must be present for MVP.

### 2.1 Unattached EBS Volumes

**US-004** I want unattached EBS volumes surfaced so I can avoid paying for storage that nothing uses.

- AC-005-1: WHEN a volume's `state` is `available` (not attached) THE SYSTEM SHALL emit a Tombstone with `cause = "abandoned"`, `severity = "wasteful"`.
- AC-005-2: IF the volume was created within the last 24 hours THE SYSTEM SHALL omit it (grace period).
- AC-005-3: THE SYSTEM SHALL include the volume size (GiB) in the Tombstone's `metadata` field.

### 2.2 Orphaned EBS Snapshots

**US-005** I want snapshots whose source volume no longer exists flagged so I can clean up orphaned backups.

- AC-006-1: WHEN a snapshot's `VolumeId` does not appear in the account's volume list THE SYSTEM SHALL emit a Tombstone with `cause = "orphaned"`, `severity = "wasteful"`.
- AC-006-2: Snapshots whose source volume exists (even if unattached) SHALL NOT be flagged by this detector.
- AC-006-3: Snapshots owned by AWS (owner `amazon` or `aws-marketplace`) SHALL be excluded.

### 2.3 Unassociated Elastic IPs

**US-006** I want idle Elastic IPs flagged because AWS charges for unassociated EIPs by the hour.

- AC-007-1: WHEN an EIP has no `AssociationId` THE SYSTEM SHALL emit a Tombstone with `cause = "idle, costs money"`, `severity = "wasteful"`.
- AC-007-2: THE SYSTEM SHALL include the public IP address in `metadata`.

### 2.4 Idle Load Balancers (ALB/NLB)

**US-007** I want load balancers with no healthy targets or zero traffic over 14 days flagged as lonely so I remove stale infrastructure.

- AC-008-1: WHEN an ALB or NLB has no registered targets in any target group THE SYSTEM SHALL emit a Tombstone with `cause = "lonely"`, `severity = "wasteful"`.
- AC-008-2: WHEN an ALB or NLB has registered targets but CloudWatch `RequestCount` (ALB) or `ActiveFlowCount` (NLB) totals zero over the last 14 days THE SYSTEM SHALL emit the same Tombstone.
- AC-008-3: THE SYSTEM SHALL query CloudWatch only once per LB using `GetMetricStatistics` with period 1209600 (14 days).
- AC-008-4: IF CloudWatch data is unavailable (permissions error or no data) THE SYSTEM SHALL fall back to target-group check only and log a warning.

### 2.5 Idle NAT Gateways

**US-008** I want NAT Gateways with near-zero traffic flagged so I stop paying ~$32/month for idle NATs.

- AC-009-1: WHEN a NAT Gateway's CloudWatch `BytesOutToDestination` total over 14 days is below the configured threshold (default 1 MB) THE SYSTEM SHALL emit a Tombstone with `cause = "idle"`, `severity = "wasteful"`.
- AC-009-2: NAT Gateways in `deleting` or `deleted` state SHALL be excluded.
- AC-009-3: IF CloudWatch data is unavailable THE SYSTEM SHALL skip the gateway and log a warning.

### 2.6 Long-Stopped EC2 Instances

**US-009** I want EC2 instances that have been stopped for 30+ days flagged because their EBS volumes still incur charges.

- AC-010-1: WHEN an instance's `State.Name` is `stopped` and the `StateTransitionReason` timestamp indicates it has been stopped for ≥ 30 days THE SYSTEM SHALL emit a Tombstone with `cause = "dead but still billed for EBS"`, `severity = "wasteful"`.
- AC-010-2: Instances stopped for fewer than 30 days SHALL NOT be flagged.
- AC-010-3: THE SYSTEM SHALL include the instance type and total attached EBS size (GiB) in `metadata`.

### 2.7 Stale IAM Access Keys

**US-010** I want IAM access keys unused for 90+ days flagged as a security risk so I can rotate or delete them.

- AC-011-1: WHEN an IAM access key's `LastUsedDate` is older than 90 days (or `LastUsedDate` is null and `CreateDate` is older than 90 days) THE SYSTEM SHALL emit a Tombstone with `cause = "undead credentials"`, `severity = "risky"`, `resource_type = "IAM::AccessKey"`.
- AC-011-2: Keys with `Status = "Inactive"` SHALL be flagged with `severity = "wasteful"` instead of `"risky"` (already disabled, but still present).
- AC-011-3: THE SYSTEM SHALL include the IAM username and key ID (not the secret) in `metadata`.
- AC-011-4: THE SYSTEM SHALL contribute to the headline "undead credentials" count in the report metadata.

### 2.8 Orphaned Security Groups

**US-011** I want security groups attached to nothing flagged so I reduce the attack surface and clutter.

- AC-012-1: WHEN a security group is not referenced by any ENI, EC2 instance, RDS instance, Lambda function, or ELB THE SYSTEM SHALL emit a Tombstone with `cause = "forgotten"`, `severity = "harmless"`.
- AC-012-2: The `default` security group for a VPC SHALL NOT be flagged (it cannot be deleted).
- AC-012-3: THE SYSTEM SHALL include the VPC ID and group name in `metadata`.

### 2.9 Oversized CloudWatch Log Groups

**US-012** I want CloudWatch log groups with no retention policy and no recent ingestion flagged so I stop accumulating unbounded log storage.

- AC-013-1: WHEN a log group has no retention policy (retentionInDays is null) AND its `metricFilterCount` is 0 AND no log events have been ingested in the last 30 days THE SYSTEM SHALL emit a Tombstone with `cause = "hoarder"`, `severity = "wasteful"`.
- AC-013-2: Log groups with an active retention policy SHALL NOT be flagged, even if quiet.
- AC-013-3: THE SYSTEM SHALL determine last-ingestion date from `storedBytes` changes or CloudWatch `IncomingLogEvents` metric over the last 30 days.
- AC-013-4: THE SYSTEM SHALL include `storedBytes` and the log group name in `metadata`.

---

## 3. Report Schema

**US-013** I want a versioned JSON schema for reports so I can validate scanner output and load it safely in the web app.

- AC-014-1: `schema/report.schema.json` SHALL be a valid JSON Schema (Draft 2020-12).
- AC-014-2: Every field in the Tombstone model SHALL have a JSON Schema definition with `type`, `description`, and where applicable `enum` or `minimum`.
- AC-014-3: THE SYSTEM SHALL include a `$schema` version string and a `generated_at` ISO-8601 timestamp in every report.
- AC-014-4: THE SYSTEM SHALL validate scanner output against the schema before writing the file; a validation failure SHALL exit code 3.
- AC-014-5: THE SYSTEM SHALL validate the seed report (`seed/report.json`) against the schema in `make test`.

---

## 4. Web App

### 4.1 General

- AC-015-1: THE SYSTEM SHALL be a static SPA built with Vite + React + TypeScript.
- AC-015-2: THE SYSTEM SHALL load `report.json` bundled at build time as the default dataset.
- AC-015-3: WHERE the user drags and drops or selects a JSON file THE SYSTEM SHALL load and validate it in-browser using the JSON Schema; if invalid, THE SYSTEM SHALL show an error and retain the previous report.
- AC-015-4: THE SYSTEM SHALL never send report data to any server. The about page SHALL state this explicitly.
- AC-015-5: THE SYSTEM SHALL escape all values sourced from the report before rendering in the DOM; `dangerouslySetInnerHTML` SHALL NOT be used.
- AC-015-6: THE SYSTEM SHALL be responsive down to 390 px viewport width.
- AC-015-7: THE SYSTEM SHALL not require any external font or image at runtime (all assets bundled).

### 4.2 Headline bar

- AC-016-1: THE SYSTEM SHALL display: total tombstone count, estimated total monthly haunting cost (labelled "estimated"), and undead-credentials count.
- AC-016-2: WHERE `demo: true` is set in the report THE SYSTEM SHALL show a "Sample Data" badge next to the headline bar.

### 4.3 Graveyard view

**US-014** As a user, I want to see zombie resources as tombstones in a graveyard scene so I immediately grasp the scale of the problem visually.

- AC-017-1: THE SYSTEM SHALL render each Tombstone as an SVG or CSS tombstone shape in a graveyard scene with a dark background, fog effect, and a moon.
- AC-017-2: Tombstone height/size SHALL be proportional to `estimated_monthly_cost`; a tombstone with zero cost SHALL still be visible at a minimum size.
- AC-017-3: Tombstone border/glow SHALL use the severity colour: green (harmless), amber (wasteful), red (risky).
- AC-017-4: WHEN a user hovers over a tombstone THE SYSTEM SHALL show an epitaph tooltip containing: resource name, type, region, died date (creation or detection date), cause of death, and estimated monthly cost labelled "estimated".
- AC-017-5: WHERE `prefers-reduced-motion` is active THE SYSTEM SHALL suppress all CSS animations (fog drift, tombstone sway, etc.).
- AC-017-6: Colour SHALL NOT be the only signal for severity; each tombstone SHALL also show a text or icon label for its severity.
- AC-017-7: All epitaph text SHALL meet WCAG AA contrast ratio (≥ 4.5:1) against its background.

### 4.4 Crypt view

**US-015** As an SRE, I want a sortable, filterable table of all zombie resources so I can triage by cost, type, region, or severity.

- AC-018-1: THE SYSTEM SHALL render all Tombstones in a table with columns: Resource Name, Type, Region, Severity, Cause of Death, Died Date, Estimated Monthly Cost.
- AC-018-2: Every column SHALL be sortable by clicking its header; the active sort column SHALL be visually indicated.
- AC-018-3: THE SYSTEM SHALL provide filter controls for: resource type (multi-select), region (multi-select), severity (multi-select).
- AC-018-4: THE SYSTEM SHALL show a row count matching the current filter.
- AC-018-5: All data available visually in the Graveyard view SHALL also be present in the Crypt table (accessibility parity).

### 4.5 Exorcism view

**US-016** As an SRE, I want a generated cleanup plan for each zombie resource so I know exactly what CLI command or Terraform change to run.

- AC-019-1: THE SYSTEM SHALL show a list of Tombstones, each with a generated cleanup plan containing: an AWS CLI command, and a Terraform removal hint (resource address).
- AC-019-2: Each command and hint SHALL have a copy-to-clipboard button.
- AC-019-3: THE SYSTEM SHALL show a "Copy All Commands" button that copies all AWS CLI commands as a shell script.
- AC-019-4: Every generated command SHALL use exact resource IDs from the report (no placeholders).
- AC-019-5: THE SYSTEM SHALL display a prominent disclaimer: "These commands will delete resources. Review carefully before running. Graveyard Shift never deletes anything itself."
- AC-019-6: Generated commands SHALL use the `--dry-run` flag where AWS CLI supports it, with a note that the user must remove it to execute.

### 4.6 About view

**US-017** As a user, I want to understand how the tool works, its read-only guarantee, and what IAM permissions are required.

- AC-020-1: THE SYSTEM SHALL describe how the scanner works in plain language.
- AC-020-2: THE SYSTEM SHALL state explicitly that no data is sent to any server.
- AC-020-3: THE SYSTEM SHALL show the exact read-only IAM policy JSON (copy button included).
- AC-020-4: THE SYSTEM SHALL list detection thresholds and their defaults.
- AC-020-5: THE SYSTEM SHALL link to the GitHub repository.

---

## 5. Static Hosting (Netlify — free tier, no AWS required)

**US-018** As a deployer, I want a one-command deploy that puts the web app on a free static host with HTTPS and proper security headers, without creating any AWS resources or incurring AWS costs.

- AC-021-1: The web app SHALL be deployable to Netlify's free tier using the Netlify CLI (`netlify deploy --prod --dir web/dist`). No AWS account, no EC2, no S3, no CloudFront is required.
- AC-021-2: A `netlify.toml` at the repo root SHALL configure: `publish = "web/dist"`, `command = "make build-web"`, SPA redirect rule (`/* → /index.html, 200`), and a `[[headers]]` block setting `Content-Security-Policy`, `X-Content-Type-Options: nosniff`, `Referrer-Policy: strict-origin-when-cross-origin`, `Strict-Transport-Security`.
- AC-021-3: Netlify serves HTTPS by default; no additional HTTP→HTTPS configuration is required.
- AC-021-4: `make deploy` SHALL run `netlify deploy --prod --dir web/dist` and print the live URL.
- AC-021-5: GitHub Pages SHALL be supported as a zero-configuration fallback: `make deploy-pages` runs `gh-pages -d web/dist`.
- AC-021-6: Both deployment targets are **optional** — the app is fully functional offline via `make demo` and `make build-web` without any deploy step.
- AC-021-7: THE SYSTEM SHALL ship a read-only IAM policy document at `infra/iam-policy.json` for users to attach to their scanner role. This file is static JSON — no CDK stack, no CloudFormation deployment, no AWS resources are created by the tool itself.

---

## 6. Cross-cutting

- AC-022-1: `make test` SHALL run pytest (scanner) and vitest (web) and exit non-zero if any test fails.
- AC-022-2: `make setup` SHALL install all Python and Node dependencies.
- AC-022-3: `make lint` SHALL run ruff (scanner) and eslint + prettier --check (web) and exit non-zero on violations.
- AC-022-4: THE SYSTEM SHALL not require any LLM or external AI service at runtime.
- AC-022-5: THE SYSTEM SHALL contain no hard-coded real AWS account IDs, real ARNs, real access keys, or real IP addresses anywhere in the repo (seed data uses account `111122223333`).
