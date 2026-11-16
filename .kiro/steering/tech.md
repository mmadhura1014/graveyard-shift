# Tech stack and conventions

## Components
1. **Scanner CLI** (`scanner/`): Python 3.12, boto3, no other runtime deps beyond `pydantic` and `click`. Command: `graveyard scan --profile X --regions a,b --out report.json` and `graveyard scan --demo` (reads seed data, no AWS calls).
2. **Detectors**: one module per detector in `scanner/detectors/`, each a pure function `detect(snapshot) -> list[Tombstone]`. Fetching AWS data is separate from detection logic so detectors are unit-testable with fixtures.
3. **Report schema**: `schema/report.schema.json` (JSON Schema), versioned. Scanner output and web app input must both validate against it.
4. **Web app** (`web/`): Vite + React + TypeScript, static SPA, no backend. Loads `report.json` (bundled demo report by default; user can drop in their own file, processed locally in the browser only).
5. **Infra** (`infra/`): the least-privilege read-only IAM policy JSON users attach to the scanner role (required). OPTIONAL stretch: a CDK (TypeScript) stack for S3 + CloudFront static hosting, validated with `cdk synth` only. **Never run `cdk deploy` or any real AWS call during development.** The developer has no sandbox AWS account (org account only, off limits).
5a. **No real AWS in dev/test/CI/demo.** The live scan path is exercised against a fake account using `moto` (in-process mock). Tests and `make demo-live` create fake zombie resources in moto, then run the real fetcher + detectors against it. Hosting for the public demo is a free static host (GitHub Pages / Netlify / Cloudflare Pages), not AWS.
6. **Seed data** (`seed/`): a realistic synthetic account snapshot and its expected report, committed to the repo.

## Detectors for MVP (cause of death in brackets)
- Unattached EBS volumes [abandoned]
- Old EBS snapshots whose source volume is gone [orphaned]
- Unassociated Elastic IPs [idle, costs money]
- ALB/NLB with no healthy targets or no traffic 14d [lonely]
- NAT Gateways with ~zero traffic 14d [idle]
- Stopped EC2 instances older than 30 days [dead but still billed for EBS]
- IAM access keys unused 90+ days [undead credentials]
- Security groups attached to nothing [forgotten]
- CloudWatch log groups with no retention and no recent ingestion [hoarder]

## Rules
- All thresholds live in one config file with defaults; document them in the README.
- Pricing: bundled `scanner/pricing.json` with a dated header. Use the AWS Pricing MCP server to verify values while building, not at runtime.
- Tests: pytest for scanner (>= 1 test per detector for positive, negative, edge), vitest for web logic. CI-free: `make test` runs all.
- One-command setup: `make setup && make demo`.
- Lint/format: ruff + eslint/prettier. Keep functions small and typed.
