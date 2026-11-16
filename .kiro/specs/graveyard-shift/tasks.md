# Tasks — Graveyard Shift

Version: 0.2 — M1 ✓, M2 ✓ (incl. moto integration tests + demo-live), M3 in progress

Milestones are sequential. Within a milestone, tasks are ordered; complete each before starting the next. Verification steps must pass before marking a task done.

---

## M1 — Scanner Skeleton, Schema, Seed Data, First 3 Detectors

Goal: a runnable CLI that reads seed data, runs three detectors, produces a schema-valid report, and passes all M1 tests.

---

### T1.1 — Project scaffolding ✅ DONE

Create the top-level directory layout:
- `scanner/`, `scanner/detectors/`, `schema/`, `seed/`, `tests/`, `tests/detectors/`, `web/`, `infra/`
- `pyproject.toml` with `[project]` metadata, `dependencies = ["boto3","pydantic>=2","click","jsonschema"]`, `[tool.ruff]`, `[tool.pytest.ini_options]`
- Root `Makefile` with targets: `setup`, `test`, `lint`, `demo`, `build-web`, `deploy` (stubs for build-web and deploy are fine now)
- `.gitignore` excluding `__pycache__`, `*.pyc`, `.venv`, `node_modules`, `cdk.out`, `dist` — but NOT `.kiro/`

**Verify:** `make setup` completes without error; `python -m pytest --collect-only` finds zero tests (passes); `git status` shows `.kiro/` is untracked (not ignored).

---

### T1.2 — JSON Schema ✅ DONE

Write `schema/report.schema.json` matching the outline in `design.md §4`.

- `$schema`: Draft 2020-12
- All required fields with types, formats, and constraints as specified
- `severity` enum: `["harmless","wasteful","risky"]`
- `estimated_monthly_cost` minimum 0

**Verify:** `python -c "import jsonschema; jsonschema.Draft202012Validator.check_schema(open('schema/report.schema.json').read() and __import__('json').load(open('schema/report.schema.json')))"` exits 0.

---

### T1.3 — Pydantic models ✅ DONE

Write `scanner/models.py` containing `Severity`, `Tombstone`, `ReportSummary`, `Report` and the `Snapshot` dataclass, as specified in `design.md §3 and §5`.

- All fields typed
- `Tombstone` validator: `estimated_monthly_cost >= 0`, `account_id` matches `^\d{12}$`
- `Report.summary` auto-computed from tombstones list (or accepted as explicit input)

**Verify:** `python -c "from scanner.models import Tombstone, Report, Snapshot"` exits 0.

---

### T1.4 — Config module ✅ DONE

Write `scanner/config.py` with a `DEFAULT_CONFIG` dict containing all thresholds:

```python
DEFAULT_CONFIG = {
    "ebs_volume_grace_period_hours": 24,
    "ec2_stopped_days": 30,
    "iam_key_unused_days": 90,
    "lb_no_traffic_days": 14,
    "nat_no_traffic_days": 14,
    "nat_min_bytes": 1_048_576,   # 1 MB
    "log_group_quiet_days": 30,
}
```

Write `scanner/config.py` to also accept an optional TOML override file.

**Verify:** `python -c "from scanner.config import DEFAULT_CONFIG; assert 'ec2_stopped_days' in DEFAULT_CONFIG"` exits 0.

---

### T1.5 — Pricing module and pricing.json ✅ DONE

Write `scanner/pricing.json` with the structure from `design.md §7` and a `last_updated` date.
Write `scanner/pricing.py` with a `get_monthly_cost(resource_type, metadata, region) -> Decimal` function.

**Verify:** `python -c "from scanner.pricing import get_monthly_cost; from decimal import Decimal; c = get_monthly_cost('EC2::Volume', {'volume_type':'gp2','size_gib':100}, 'us-east-1'); assert c >= 0"` exits 0.

---

### T1.6 — Seed snapshot ✅ DONE

Write `seed/snapshot.json`: a realistic synthetic Snapshot serialised as JSON using fake account `111122223333`. Must include at least:
- 3 unattached EBS volumes (different types/sizes)
- 2 orphaned snapshots
- 2 unassociated EIPs
- 1 stopped EC2 instance (stopped 45 days ago)
- 1 idle ALB (no targets)
- 1 idle NAT gateway
- 2 stale IAM access keys
- 2 orphaned security groups
- 2 log groups matching the hoarder pattern
- Enough non-zombie resources to test negative cases

No real IDs, real account numbers, real IPs, or real ARNs. All account IDs must be `111122223333`.

**Verify:** `python -c "import json; d = json.load(open('seed/snapshot.json')); assert d['account_id'] == '111122223333'"` exits 0.

---

### T1.7 — Detector: unattached EBS volumes (`ebs_volumes.py`) ✅ DONE

Implement `scanner/detectors/ebs_volumes.py` with `detect(snapshot, config) -> list[Tombstone]`.

Logic:
- For each region, iterate volumes
- Flag volumes with `state == "available"` created more than `config["ebs_volume_grace_period_hours"]` hours ago
- Tombstone fields: `cause="abandoned"`, `severity="wasteful"`, `resource_type="EC2::Volume"`, `metadata` includes `size_gib` and `volume_type`
- `exorcism_cli`: `aws ec2 delete-volume --volume-id {id} --region {region} --dry-run`
- `exorcism_tf`: `resource "aws_ebs_volume" "{sanitised_name}" {}`

Write tests in `tests/detectors/test_ebs_volumes.py`:
- **positive**: volume in `available` state older than grace period → 1 tombstone
- **negative**: volume in `in-use` state → 0 tombstones
- **edge**: volume in `available` state within grace period → 0 tombstones
- **property P1**: snapshot not mutated
- **property P2**: cost ≥ 0
- **property P3**: deterministic

**Verify:** `pytest tests/detectors/test_ebs_volumes.py -v` all pass.

---

### T1.8 — Detector: orphaned EBS snapshots (`ebs_snapshots.py`) ✅ DONE

Implement `scanner/detectors/ebs_snapshots.py`.

Logic:
- Collect all volume IDs in the snapshot
- Flag snapshots whose `VolumeId` is not in that set, excluding AWS-owned snapshots
- `cause="orphaned"`, `severity="wasteful"`, `resource_type="EC2::Snapshot"`
- `exorcism_cli`: `aws ec2 delete-snapshot --snapshot-id {id} --region {region} --dry-run`

Write tests in `tests/detectors/test_ebs_snapshots.py`:
- **positive**: snapshot with volume ID not in volumes list → flagged
- **negative**: snapshot whose volume exists (even if unattached) → not flagged
- **negative**: AWS-owned snapshot → not flagged
- **edge**: empty volumes list, non-AWS snapshot → flagged

**Verify:** `pytest tests/detectors/test_ebs_snapshots.py -v` all pass.

---

### T1.9 — Detector: unassociated Elastic IPs (`elastic_ips.py`) ✅ DONE

Implement `scanner/detectors/elastic_ips.py`.

Logic:
- Flag addresses with no `AssociationId`
- `cause="idle, costs money"`, `severity="wasteful"`, `resource_type="EC2::EIP"`
- `metadata` includes `public_ip`
- `exorcism_cli`: `aws ec2 release-address --allocation-id {id} --region {region} --dry-run`

Write tests in `tests/detectors/test_elastic_ips.py`:
- **positive**: EIP with no AssociationId → flagged
- **negative**: EIP with AssociationId → not flagged
- **edge**: empty EIP list → empty result

**Verify:** `pytest tests/detectors/test_elastic_ips.py -v` all pass.

---

### T1.10 — CLI skeleton and demo mode ✅ DONE

Write `scanner/cli.py` (click entry point) and `scanner/report.py` (assembles and validates Report).

CLI command: `graveyard scan --demo --out report.json`
- `--demo` loads `seed/snapshot.json`, runs `ALL_DETECTORS`, calls `report.py`, writes output
- `report.py` validates against `schema/report.schema.json` using `jsonschema`; exits 3 on failure

Write `scanner/detectors/__init__.py` exporting `ALL_DETECTORS` (list of detect functions; for now only the 3 M1 detectors).

Wire up `pyproject.toml` entry point: `graveyard = "scanner.cli:main"`.

Update `Makefile` `demo` target: `graveyard scan --demo --out /tmp/graveyard-demo-report.json && echo "Report written to /tmp/graveyard-demo-report.json"`.

**Verify:**
1. `pip install -e .` succeeds
2. `graveyard scan --demo --out /tmp/test-report.json` exits 0
3. `python -c "import json,jsonschema; schema=json.load(open('schema/report.schema.json')); report=json.load(open('/tmp/test-report.json')); jsonschema.validate(report, schema)"` exits 0
4. `python -c "import json; r=json.load(open('/tmp/test-report.json')); assert r['demo'] == True"` exits 0

---

### T1.11 — M1 test suite and seed report ✅ DONE

Write `tests/conftest.py` with fixtures: `seed_snapshot`, `default_config`.
Write `seed/report.json` by running `graveyard scan --demo --out seed/report.json`.
Add `make test` to run `pytest tests/ -v`.

**Verify:**
1. `make test` exits 0
2. `python -c "import json,jsonschema; schema=json.load(open('schema/report.schema.json')); report=json.load(open('seed/report.json')); jsonschema.validate(report, schema)"` exits 0
3. `seed/report.json` contains tombstones only for the zombie resources in `seed/snapshot.json`, not clean resources

---

## M2 — Remaining 6 Detectors, Pricing, CLI Polish

Goal: all 9 detectors passing tests; `make demo` produces a complete, fully-priced seed report; `make lint` clean.

---

### T2.1 — Detector: idle load balancers (`load_balancers.py`) ✅ DONE

Logic per AC-008-1 through AC-008-4.
- `cause="lonely"`, `severity="wasteful"`, `resource_type="ELB::LoadBalancer"`
- `metadata` includes `lb_type` (ALB/NLB) and `dns_name`
- CloudWatch fallback on permission error

Tests: positive (no targets), positive (targets but zero traffic), negative (healthy targets + traffic), edge (CW unavailable → fallback to target check).

**Verify:** `pytest tests/detectors/test_load_balancers.py -v` all pass.

---

### T2.2 — Detector: idle NAT gateways (`nat_gateways.py`) ✅ DONE

Logic per AC-009-1 through AC-009-3.
- `cause="idle"`, `severity="wasteful"`, `resource_type="EC2::NatGateway"`
- `metadata` includes `vpc_id` and `subnet_id`
- `exorcism_cli`: `aws ec2 delete-nat-gateway --nat-gateway-id {id} --region {region}`
  (NAT GW delete has no `--dry-run`; note that in the exorcism output)

Tests: positive (< 1 MB over 14 days), negative (above threshold), edge (deleting/deleted state excluded), edge (CW unavailable → skipped with warning).

**Verify:** `pytest tests/detectors/test_nat_gateways.py -v` all pass.

---

### T2.3 — Detector: stopped EC2 instances (`ec2_stopped.py`) ✅ DONE (regex fixed for GMT|UTC)

Logic per AC-010-1 through AC-010-3.
- Parse `StateTransitionReason` string for stop timestamp (format: `"User initiated (2024-11-01 10:23:45 GMT)"`)
- `cause="dead but still billed for EBS"`, `severity="wasteful"`, `resource_type="EC2::Instance"`
- `metadata` includes `instance_type` and `ebs_size_gib`
- `exorcism_cli`: `aws ec2 terminate-instances --instance-ids {id} --region {region} --dry-run`

Tests: positive (stopped 45 days ago), negative (stopped 10 days ago), negative (running), edge (unparseable StateTransitionReason → use launch time as fallback or skip), property P3 (deterministic).

**Verify:** `pytest tests/detectors/test_ec2_stopped.py -v` all pass.

---

### T2.4 — Detector: stale IAM access keys (`iam_keys.py`) ✅ DONE

Logic per AC-011-1 through AC-011-4.
- `cause="undead credentials"`, `severity="risky"` (active key) or `"wasteful"` (inactive key)
- `resource_type="IAM::AccessKey"`, `region="global"`
- `metadata` includes `username` and `key_id` (not secret key)
- `exorcism_cli`: `aws iam delete-access-key --access-key-id {key_id} --user-name {username}`
- Contributes to `undead_credentials_count` in summary

Tests: positive (active key, last used 100 days ago), positive (key never used, created 100 days ago), negative (used 10 days ago), positive-inactive (inactive key, old), property P2 (cost = 0 for IAM keys is acceptable; they carry no direct cost).

**Verify:** `pytest tests/detectors/test_iam_keys.py -v` all pass.

---

### T2.5 — Detector: orphaned security groups (`security_groups.py`) ✅ DONE

Logic per AC-012-1 through AC-012-3.
- Check ENI references, instance references (from instances snapshot), RDS (if available; skip if not in snapshot), ELB references
- Exclude `default` SGs
- `cause="forgotten"`, `severity="harmless"`, `resource_type="EC2::SecurityGroup"`
- `metadata` includes `vpc_id` and `group_name`
- `exorcism_cli`: `aws ec2 delete-security-group --group-id {id} --region {region} --dry-run`

Tests: positive (SG not referenced anywhere), negative (SG attached to ENI), negative (default SG), edge (empty ENI and instance lists).

**Verify:** `pytest tests/detectors/test_security_groups.py -v` all pass.

---

### T2.6 — Detector: hoarder log groups (`log_groups.py`) ✅ DONE

Logic per AC-013-1 through AC-013-4.
- No retention policy AND no metric filters AND no ingestion in last 30 days
- Determine quiet period from CloudWatch `IncomingLogEvents` metric or `storedBytes` being 0
- `cause="hoarder"`, `severity="wasteful"`, `resource_type="CWLogs::LogGroup"`
- `metadata` includes `log_group_name` and `stored_bytes`
- `exorcism_cli`: `aws logs delete-log-group --log-group-name {name} --region {region}`

Tests: positive (no retention, no filters, zero IncomingLogEvents 30d), negative (has retention policy), negative (has metric filters), edge (storedBytes = 0 and no CW data → flag).

**Verify:** `pytest tests/detectors/test_log_groups.py -v` all pass.

---

### T2.7 — Pricing coverage for all resource types ✅ DONE

Extend `pricing.json` and `pricing.py` to cover all 9 detector types. Verify unit prices against the AWS Pricing MCP server. Add `last_updated` date.

Spot-check prices (before coding, verify with MCP):
- EBS gp2: $0.10/GB-month us-east-1
- EIP unassociated: $0.005/hr
- NAT Gateway: $0.045/hr + $0.045/GB
- ALB: $0.008/hr (LCU pricing excluded; use hourly only for estimate)
- NLB: $0.006/hr
- CW Logs storage: $0.03/GB-month

**Verify:** `python -c "from scanner.pricing import get_monthly_cost; from decimal import Decimal; assert get_monthly_cost('EC2::EIP', {}, 'us-east-1') > 0"` exits 0.

---

### T2.8 — Update ALL_DETECTORS and seed report ✅ DONE

Add all 6 new detectors to `scanner/detectors/__init__.py`'s `ALL_DETECTORS` list.
Regenerate `seed/report.json` with `graveyard scan --demo --out seed/report.json`.

**Verify:**
1. `make test` exits 0 (all 9 detector test files pass)
2. `seed/report.json` summary has `total_tombstones` matching the count of zombie resources in `seed/snapshot.json`
3. Schema validation passes on `seed/report.json`

---

### T2.9 — Fetcher implementation ✅ DONE (moto integration test added)

Write `scanner/fetcher.py` implementing `fetch(session, regions, config) -> Snapshot`.
- Paginate all API calls
- Parallel region fetch with `ThreadPoolExecutor(max_workers=8)`
- Skip region on `AuthFailure` / `UnauthorizedOperation`, log WARNING, set exit code 2
- Do not log full ARNs or credentials at INFO level

**Verify:** Unit test with mocked boto3 (`moto` or `unittest.mock`) covering: single region, multi-region parallel, region auth failure skipped gracefully.

---

### T2.10 — Live scan CLI path ✅ DONE

Wire `--profile`, `--regions`, `--out`, `--config`, `--verbose` flags to call the fetcher.
- `graveyard scan --profile X --regions us-east-1 --out report.json`
- `--verbose` sets log level to DEBUG

(No AWS credentials required to verify; test with mock session.)

**Verify:** `graveyard scan --help` shows all flags with descriptions; `graveyard scan --demo` still works; `make lint` exits 0.

---

### T2.11 — Property-based tests (P1–P12)

Add `tests/test_properties.py` covering properties P1–P12 from `design.md §12`.
Use `pytest.mark.parametrize` or Hypothesis (if installed) for P2, P3, P7, P8.

**Verify:** `pytest tests/test_properties.py -v` all pass.

---

### T2.12 — Lint clean ✅ DONE

Run `ruff check scanner/ tests/` and fix all violations. Run `ruff format scanner/ tests/`.

**Verify:** `make lint` exits 0 (ruff returns 0).

---

### T2.13 — moto integration tests (real fetcher + detectors against mock AWS) ✅ DONE

Added `freezegun` dev dep. Wrote `tests/test_moto_fetcher_integration.py`:
- Creates fake zombie resources in an in-process moto mock (unattached EBS, idle EIP, stopped EC2, orphaned snapshot, unused IAM key, empty SG, target-less ALB, retention-less log group) using fake credentials only (`AWS_ACCESS_KEY_ID=testing`).
- Runs the REAL `scanner.fetcher.fetch()` + `ALL_DETECTORS` against the mock.
- Asserts each detector finds its expected zombie.
- Builds a full report and validates it against `schema/report.schema.json`.
- Documents the stated limitation: moto does NOT populate CloudWatch metrics for NAT Gateway / ALB / log groups, so the NAT/ALB traffic-based detectors cannot be fully exercised here — they are covered by fixture unit tests instead.
- Found and fixed a real bug: the stopped-EC2 detector's `StateTransitionReason` regex only accepted the `GMT` suffix, but AWS (and moto) also uses `UTC`. Fixed regex to accept both.

**Verify:** `pytest tests/test_moto_fetcher_integration.py -v` → 4/4 pass.

---

### T2.14 — `make demo-live` target ✅ DONE

Added `scripts/moto_demo_scan.py` and `make demo-live` target. Runs the real fetcher + detectors against an in-process moto mock with fake credentials. Never touches real AWS.

**Verify:** `make demo-live` writes a schema-valid report to `/tmp/graveyard-live.json`. Note: moto auto-creates ~1300 AMI snapshots with non-AWS owner IDs, so the snapshot detector flags them all — this is correct detector behavior (the source volumes don't exist in the mock account), not a bug.

---

## M3 — Web App (all four views)

Goal: `make build-web` succeeds; opening `web/dist/index.html` locally shows all four views with the demo report; vitest passes.

---

### T3.1 — Vite + React + TypeScript scaffold

```
cd web && npm create vite@latest . -- --template react-ts
```

Install additional deps: `zustand`, `react-router-dom`, `ajv`, `ajv-formats`.
Install dev deps: `vitest`, `@testing-library/react`, `eslint`, `prettier`, `@typescript-eslint/eslint-plugin`.

Copy `seed/report.json` to `web/src/assets/demo-report.json`.
Configure Vite to import JSON and to hash asset filenames.

**Verify:** `cd web && npm run dev` starts without error; browser shows Vite default page.

---

### T3.2 — Schema validation util and report store

Write `web/src/utils/schema.ts`: imports the JSON Schema, creates an `ajv` validator, exports `validateReport(data: unknown): Report | null`.
Write `web/src/store/reportStore.ts`: Zustand store with `report: Report | null`, `setReport`, `clearReport`, `activeView`.
Write `web/src/hooks/useReport.ts`: on mount, loads and validates `demo-report.json`, calls `setReport`.

**Verify:** `cd web && npx vitest run src/utils/schema.test.ts` — write one test: valid demo report passes validation; malformed object returns null.

---

### T3.3 — HeadlineBar component

Displays: tombstone count, estimated monthly cost (formatted "$X.XX/mo (estimated)"), undead-credentials count, and "Sample Data" badge when `demo: true`.

**Verify:** vitest: `HeadlineBar` renders correct counts from a fixture report; badge appears when `demo: true`; badge absent when `demo: false`.

---

### T3.4 — Crypt view (sortable, filterable table)

Implements AC-018-1 through AC-018-5.
- Columns: Resource Name, Type, Region, Severity, Cause of Death, Died Date, Est. Monthly Cost
- Sort on column header click (ascending/descending toggle, sort indicator)
- Filters: type, region, severity (multi-select dropdowns or checkbox groups)
- Row count display

Write `web/src/hooks/useFilter.ts` to encapsulate filter/sort state.

**Verify:**
1. vitest: `useFilter` sorts by cost descending correctly; filter by severity removes non-matching rows
2. Visual check: all columns render; filters work in `npm run dev`

---

### T3.5 — SeverityBadge component

Renders severity with both a coloured glow/chip AND a text label (not colour alone).
Colours: green (#4ade80 or similar low-saturation) for harmless, amber (#fbbf24) for wasteful, red (#f87171) for risky.
Contrast against dark background ≥ 4.5:1 (WCAG AA).

**Verify:** vitest: all three severity values render the correct text label and correct CSS class/colour token.

---

### T3.6 — Tombstone component and Graveyard view

Implements AC-017-1 through AC-017-7.
- Graveyard scene: dark `#0d0d14` background, CSS moon (or bundled SVG), CSS/SVG fog layer
- Each tombstone: SVG or CSS shape, height proportional to cost (min-height for zero-cost items), severity-coloured border glow + severity text label
- Hover: epitaph tooltip (resource name, type, region, died date, cause, estimated cost)
- `prefers-reduced-motion`: all CSS animations disabled via `@media (prefers-reduced-motion: reduce)`
- No `dangerouslySetInnerHTML`; all tomb labels via escaped text nodes

**Verify:**
1. vitest: `Tombstone` renders with the correct severity class for each severity value
2. Visual check in `npm run dev`: graveyard scene visible with demo tombstones; hover tooltip shows all epitaph fields

---

### T3.7 — Exorcism view

Implements AC-019-1 through AC-019-6.
- List of tombstones, each card showing: resource name, `exorcism_cli` (copy button), `exorcism_tf` hint (copy button)
- "Copy All Commands" button → clipboard with all CLI commands as a shell script
- Disclaimer banner: "These commands will delete resources. Review carefully before running. Graveyard Shift never deletes anything itself."
- Commands containing `--dry-run` show note: "Remove --dry-run to execute."
- All resource IDs in commands come from the report (no placeholders)

**Verify:**
1. vitest: "Copy All Commands" assembles commands from all tombstones in correct order
2. vitest: disclaimer text is present in rendered output
3. Visual check: copy buttons visible; disclaimer prominent

---

### T3.8 — About view

Implements AC-020-1 through AC-020-5.
- How it works (3–4 paragraphs)
- "No data leaves your browser" statement
- IAM policy JSON block with copy button (fetched from bundled `infra/iam-policy.json` or inlined as a constant)
- Threshold defaults table
- GitHub link (placeholder URL until repo is public)

**Verify:** Visual check: all five content sections present; IAM policy copy button works.

---

### T3.9 — FileDropZone component

Implements AC-015-3.
- Drag-and-drop zone and "Open file" button
- On file select: parse JSON, validate with `validateReport`, if valid call `setReport`, if invalid show toast error and retain previous report
- Toast: accessible (role="alert"), auto-dismisses after 5 s
- File is never sent to any server (purely in-browser)

**Verify:**
1. vitest: valid report file → `setReport` called; invalid JSON → error toast; schema-invalid JSON → error toast
2. Visual check: drop zone visible; error toast appears on bad file

---

### T3.10 — Navigation, routing, responsive layout

Wire `react-router-dom` hash router with four routes: `/`, `/crypt`, `/exorcism`, `/about`.
Nav bar with four labelled tabs.
Responsive layout: works at 390 px (single-column nav collapses to hamburger or stacked tabs).
No external fonts. Use `font-family: system-ui, sans-serif`.

**Verify:**
1. vitest: all four routes render without error
2. Visual check at 390 px viewport width in browser devtools

---

### T3.11 — Web vitest suite and lint

Write `web/src/utils/escape.test.ts`: verify HTML-special characters are escaped in display helpers.
Run `eslint src/ --max-warnings 0` and `prettier --check src/`.

**Verify:** `cd web && npx vitest run` all pass; `npm run lint` exits 0.

---

## M4 — CDK Hosting, IAM Policy, README, One-Command Setup

Goal: `make deploy` works; `make setup && make demo` works on a fresh machine (macOS/Linux); README complete.

---

---

### T4.1 — IAM policy file

Write `infra/iam-policy.json` with the exact policy from `design.md §8`.
This is a **static JSON file only** — no CDK, no CloudFormation, no AWS resources are created.
Verify no write permissions are present (automated check: assert no action starts with `Create`, `Delete`, `Put`, `Update`, `Terminate`, `Modify`, `Attach`, `Detach`).

**Verify:** `python -c "import json; p=json.load(open('infra/iam-policy.json')); actions=[a for s in p['Statement'] for a in s['Action']]; bad=[a for a in actions if any(a.startswith(v) for v in ['Create','Delete','Put','Update','Terminate','Modify','Attach','Detach'])]; assert bad == [], bad"` exits 0.

---

### T4.2 — netlify.toml and static hosting config

Write `netlify.toml` at the repo root:
```toml
[build]
  command = "make build-web"
  publish  = "web/dist"

[[redirects]]
  from   = "/*"
  to     = "/index.html"
  status = 200

[[headers]]
  for = "/*"
  [headers.values]
    Content-Security-Policy           = "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'"
    X-Content-Type-Options            = "nosniff"
    Referrer-Policy                   = "strict-origin-when-cross-origin"
    Strict-Transport-Security         = "max-age=63072000; includeSubDomains"
```

Add a `404.html` to `web/public/` that redirects to `index.html` (needed for GitHub Pages SPA routing).

**Verify:** `cat netlify.toml` shows all four sections; `make build-web` exits 0 and `web/dist/index.html` exists.

---

### T4.3 — GitHub Pages fallback

Install `gh-pages` as a dev dependency in `web/package.json`.
Add to root `Makefile`:
```makefile
deploy-pages:
	cd web && npx gh-pages -d dist
```

No AWS account needed. GitHub Pages is free for public repos.

**Verify:** `make deploy-pages --dry-run` (or `echo` stub) exits 0; `gh-pages` is listed in `web/package.json` devDependencies.

---

### T4.4 — Makefile completeness

Implement all Makefile targets:
- `setup`: `pip install -e ".[dev]"` + `cd web && npm ci`
- `demo`: `graveyard scan --demo --out /tmp/graveyard-demo.json && echo "Done: /tmp/graveyard-demo.json"`
- `test`: `pytest tests/ -v && cd web && npx vitest run`
- `lint`: `ruff check scanner/ tests/ && ruff format --check scanner/ tests/ && cd web && npm run lint`
- `build-web`: `cd web && npm run build`
- `deploy`: `make build-web && netlify deploy --prod --dir web/dist` (requires `netlify login` first; prints live URL)
- `deploy-pages`: `make build-web && cd web && npx gh-pages -d dist`

No AWS credentials, no AWS account, no CDK required for any of these targets.

**Verify:** `make setup` completes on a fresh clone (Python 3.12 and Node 20 assumed); `make demo` exits 0; `make build-web` exits 0 and `web/dist/index.html` exists.

---

### T4.5 — README

Write `README.md` covering:
1. What it is (one paragraph)
2. Quick start: `make setup && make demo`
3. Live scan: `graveyard scan --profile X --regions us-east-1,eu-west-1 --out report.json`
4. Threshold configuration table (all keys from `config.py` with defaults and descriptions)
5. All 9 detectors: name, cause, severity, what it checks
6. IAM policy (verbatim JSON block)
7. Hosting: `make deploy` (Netlify) or `make deploy-pages` (GitHub Pages) — both free, no AWS account needed
8. How to load a custom report into the web app
9. Honesty note: "Cost figures are estimates. Demo data is synthetic."
10. Kiroween submission note

**Verify:** README renders correctly on GitHub (check heading hierarchy, code blocks, table formatting).

---

## M5 — Polish, Demo Assets, Submission

Goal: 3-minute demo runs end-to-end from seed data on any machine; `/.kiro` contents demonstrate all judging criteria; submission docs complete.

---

### T5.1 — Kiro automation files

Create `.kiro/hooks/` directory and write hook config files as approved in `automation-proposal.md`.

**Verify:** Hooks directory exists and contains valid hook config files.

---

### T5.2 — MCP configuration

Write `.kiro/settings/mcp.json` as specified in `automation-proposal.md`.

**Verify:** `.kiro/settings/mcp.json` is valid JSON; no real credentials are embedded.

---

### T5.3 — Design polish pass (web app)

- Review all four views at 390 px and 1440 px
- Check fog animation respects `prefers-reduced-motion`
- Verify WCAG AA contrast on all severity badge text
- Verify tombstone severity label is text-visible (not colour-only)
- Check all copy buttons work and show feedback (brief "Copied!" state)
- Verify "Sample Data" banner appears on demo report

**Verify:** Manual visual review checklist complete; no console errors in browser.

---

### T5.4 — Seed data review

Review `seed/snapshot.json` and `seed/report.json`:
- No real account IDs (must be `111122223333` throughout)
- No real IPs, real ARNs, real key IDs
- Tombstone epitaphs are interesting and varied for demo purposes
- Cost estimates are labelled "estimated" in report metadata

**Verify:** `grep -r "(?!111122223333)\b\d{12}\b" seed/` returns no matches; `python -c "import json; r=json.load(open('seed/report.json')); assert r['demo'] == True"` exits 0.

---

### T5.5 — End-to-end demo script

Write `demo/DEMO_SCRIPT.md` describing the 3-minute walkthrough:
1. `make setup && make demo` — show CLI output
2. Open web app — show headline numbers
3. Graveyard view — hover a tombstone, read epitaph
4. Crypt view — sort by cost, filter by severity=risky
5. Exorcism view — show cleanup commands, copy one
6. About view — show IAM policy, "no data leaves your browser"
7. Drop a custom report JSON — show it loads locally
8. (Optional) `make deploy` → show live Netlify URL (free, no AWS account)

**Verify:** Follow the script in a clean terminal; each step works as described.

---

### T5.6 — Final submission checklist

- [ ] `.kiro/specs/graveyard-shift/` has all four spec files
- [ ] `.kiro/steering/` has all four steering files
- [ ] `.kiro/hooks/` exists with valid hook configs
- [ ] `.kiro/settings/mcp.json` exists
- [ ] `.kiro/` is NOT in `.gitignore`
- [ ] `make setup && make demo` works on a clean clone
- [ ] `make test` exits 0
- [ ] `make lint` exits 0
- [ ] `make build-web` exits 0 and `web/dist/index.html` exists
- [ ] `seed/report.json` validates against schema
- [ ] No real account IDs, keys, or ARNs in repo
- [ ] `README.md` complete
- [ ] `infra/iam-policy.json` present and read-only (static JSON, no CDK)
- [ ] `netlify.toml` present with security headers and SPA redirect
- [ ] `demo/DEMO_SCRIPT.md` complete
- [ ] No AWS account, EC2, S3, CloudFront, or CDK resources created by the tool

**Verify:** All checklist items ticked.
