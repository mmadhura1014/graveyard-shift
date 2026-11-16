# Design — Graveyard Shift

Version: 0.1 (pre-implementation, awaiting approval)

---

## 1. System Overview

Graveyard Shift has three independently deployable components that share one data contract (`report.json`):

```
┌─────────────────────────────────────────────────────────────┐
│  AWS Account (read-only APIs)                                │
│  EC2 / EBS / EIP / ELB / NAT GW / IAM / SG / CW Logs       │
└────────────────────┬────────────────────────────────────────┘
                     │  boto3 Describe*/List*/Get* only
                     ▼
┌─────────────────────────────────────────────────────────────┐
│  Scanner CLI  (scanner/)  Python 3.12 + boto3 + pydantic    │
│                                                              │
│  fetcher.py ──► Snapshot  ──► detectors/ ──► [Tombstone]    │
│                                      │                       │
│                                      ▼                       │
│                               pricing.py ──► cost estimates  │
│                                      │                       │
│                                      ▼                       │
│                               report.py ──► report.json      │
│                               (validates against schema)     │
└──────────────────────────────────────┬──────────────────────┘
                                       │  report.json
                     ┌─────────────────┼──────────────────────┐
                     │                 │  demo mode            │
                     │       seed/snapshot.json ──► detectors  │
                     │       seed/report.json (expected output)│
                     └─────────────────┬──────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────┐
│  Web App  (web/)  Vite + React + TypeScript  (static SPA)   │
│                                                              │
│  Loads bundled report.json (or user file-drop, local only)  │
│  Views: Graveyard │ Crypt │ Exorcism │ About                │
└─────────────────────────────────────────────────────────────┘
                     deployed via (no AWS resources)
┌─────────────────────────────────────────────────────────────┐
│  Netlify free tier  (netlify.toml)                          │
│  — OR —                                                      │
│  GitHub Pages  (make deploy-pages)                          │
│  — OR —                                                      │
│  Open web/dist/index.html locally (zero infra)              │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. Data Flow

### 2.1 Live scan

1. CLI parses flags (`--profile`, `--regions`, `--out`, `--config`).
2. `fetcher.py` creates a boto3 session and calls read-only APIs across each requested region, collecting raw API responses into a `Snapshot` object.
3. The `Snapshot` is passed—unchanged—to each detector module.
4. Each detector returns a `list[Tombstone]`; the results are merged.
5. `pricing.py` looks up unit costs from `scanner/pricing.json` and annotates each Tombstone with `estimated_monthly_cost`.
6. `report.py` assembles the final `Report` object, validates it against `schema/report.schema.json`, and writes to `--out`.

### 2.2 Demo mode

Steps 1 and 2 are replaced by loading `seed/snapshot.json` from the package. Steps 3–6 are identical to live scan. The resulting report has `demo: true`.

### 2.3 Web app load

On startup the web app imports the bundled demo `report.json`. If the user drops a custom file, it is validated in-browser with the same JSON Schema (compiled to JS via `ajv`). The file never leaves the browser.

---

## 3. Tombstone Data Model

```python
# scanner/models.py  (Pydantic v2)

from __future__ import annotations
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any
import uuid

class Severity(StrEnum):
    HARMLESS = "harmless"   # green glow
    WASTEFUL = "wasteful"   # amber glow
    RISKY    = "risky"      # red glow

class Tombstone(BaseModel):
    id: str                        # UUID v4, stable within a report
    resource_id: str               # AWS resource ID (e.g. vol-0abc123)
    resource_name: str | None      # from Name tag, may be absent
    resource_type: str             # e.g. "EC2::Volume"
    region: str                    # e.g. "us-east-1"
    account_id: str                # 12-digit AWS account ID
    cause: str                     # human-readable cause of death
    severity: Severity
    detected_at: datetime          # when the scan ran (ISO-8601)
    created_at: datetime | None    # resource creation time, if available
    estimated_monthly_cost: Decimal  # >= 0; labelled "estimated" everywhere
    metadata: dict[str, Any]       # detector-specific extra fields
    exorcism_cli: str              # exact AWS CLI command(s)
    exorcism_tf: str               # Terraform resource address hint

class Report(BaseModel):
    schema_version: str            # e.g. "1.0"
    generated_at: datetime
    demo: bool
    account_id: str
    regions_scanned: list[str]
    scan_duration_seconds: float
    tombstones: list[Tombstone]
    summary: ReportSummary

class ReportSummary(BaseModel):
    total_tombstones: int
    estimated_monthly_cost: Decimal   # sum of all tombstones
    undead_credentials_count: int     # IAM::AccessKey tombstones only
    by_severity: dict[str, int]       # {"harmless": N, "wasteful": N, "risky": N}
    by_type: dict[str, int]
```

**Key invariants (checked at construction):**
- `estimated_monthly_cost >= 0`
- `severity` is one of the three enum values
- `region` matches `^[a-z]{2}-[a-z]+-\d$` (or `global` for IAM)
- `account_id` matches `^\d{12}$`
- `exorcism_cli` is non-empty
- `id` is a valid UUID

---

## 4. JSON Schema Outline

`schema/report.schema.json` mirrors the Pydantic model and is used for:
- server-side validation before writing the report file
- in-browser validation when a user drops a custom file

```jsonc
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://github.com/…/graveyard-shift/schema/report.schema.json",
  "title": "GraveyardShiftReport",
  "type": "object",
  "required": ["schema_version","generated_at","demo","account_id",
               "regions_scanned","scan_duration_seconds","tombstones","summary"],
  "properties": {
    "schema_version": { "type": "string", "pattern": "^\\d+\\.\\d+$" },
    "generated_at":   { "type": "string", "format": "date-time" },
    "demo":           { "type": "boolean" },
    "account_id":     { "type": "string", "pattern": "^\\d{12}$" },
    "regions_scanned":{ "type": "array", "items": { "type": "string" } },
    "scan_duration_seconds": { "type": "number", "minimum": 0 },
    "tombstones": {
      "type": "array",
      "items": { "$ref": "#/$defs/Tombstone" }
    },
    "summary": { "$ref": "#/$defs/ReportSummary" }
  },
  "$defs": {
    "Tombstone": {
      "type": "object",
      "required": ["id","resource_id","resource_type","region","account_id",
                   "cause","severity","detected_at","estimated_monthly_cost",
                   "metadata","exorcism_cli","exorcism_tf"],
      "properties": {
        "id":                     { "type": "string", "format": "uuid" },
        "resource_id":            { "type": "string", "minLength": 1 },
        "resource_name":          { "type": ["string","null"] },
        "resource_type":          { "type": "string", "minLength": 1 },
        "region":                 { "type": "string" },
        "account_id":             { "type": "string", "pattern": "^\\d{12}$" },
        "cause":                  { "type": "string", "minLength": 1 },
        "severity":               { "type": "string", "enum": ["harmless","wasteful","risky"] },
        "detected_at":            { "type": "string", "format": "date-time" },
        "created_at":             { "type": ["string","null"], "format": "date-time" },
        "estimated_monthly_cost": { "type": "number", "minimum": 0 },
        "metadata":               { "type": "object" },
        "exorcism_cli":           { "type": "string", "minLength": 1 },
        "exorcism_tf":            { "type": "string" }
      }
    },
    "ReportSummary": {
      "type": "object",
      "required": ["total_tombstones","estimated_monthly_cost",
                   "undead_credentials_count","by_severity","by_type"],
      "properties": {
        "total_tombstones":          { "type": "integer", "minimum": 0 },
        "estimated_monthly_cost":    { "type": "number",  "minimum": 0 },
        "undead_credentials_count":  { "type": "integer", "minimum": 0 },
        "by_severity": {
          "type": "object",
          "properties": {
            "harmless": { "type": "integer", "minimum": 0 },
            "wasteful": { "type": "integer", "minimum": 0 },
            "risky":    { "type": "integer", "minimum": 0 }
          }
        },
        "by_type": { "type": "object", "additionalProperties": { "type": "integer" } }
      }
    }
  }
}
```

---

## 5. Fetcher / Snapshot Design

`fetcher.py` builds a `Snapshot` dataclass containing raw API responses. Each field is a plain Python list of dicts (the raw boto3 response payloads, not parsed). Detectors receive the Snapshot and must not modify it.

```python
@dataclass
class Snapshot:
    account_id: str
    regions: list[str]
    scanned_at: datetime

    # Per-region dicts keyed by region string
    volumes:          dict[str, list[dict]]   # ec2.describe_volumes
    snapshots:        dict[str, list[dict]]   # ec2.describe_snapshots (owner=self)
    elastic_ips:      dict[str, list[dict]]   # ec2.describe_addresses
    load_balancers:   dict[str, list[dict]]   # elbv2.describe_load_balancers
    target_groups:    dict[str, list[dict]]   # elbv2.describe_target_groups
    target_health:    dict[str, list[dict]]   # elbv2.describe_target_health (all TG arns)
    nat_gateways:     dict[str, list[dict]]   # ec2.describe_nat_gateways
    instances:        dict[str, list[dict]]   # ec2.describe_instances
    security_groups:  dict[str, list[dict]]   # ec2.describe_security_groups
    enis:             dict[str, list[dict]]   # ec2.describe_network_interfaces
    log_groups:       dict[str, list[dict]]   # logs.describe_log_groups
    cw_metrics:       dict[str, list[dict]]   # cloudwatch.get_metric_statistics results

    # Global (no region key)
    iam_users:        list[dict]              # iam.list_users
    iam_access_keys:  list[dict]              # iam.list_access_keys + get_access_key_last_used
```

**Fetcher principles:**
- One boto3 session per region; paginates all list calls.
- Skips a region on `ClientError` with code `AuthFailure` or `UnauthorizedOperation`, logs the skip at WARNING level, and sets exit code 2 on completion.
- Uses `ThreadPoolExecutor(max_workers=8)` for parallel region fetching.

---

## 6. Detector Module Contract

```
scanner/detectors/
    __init__.py          # exports ALL_DETECTORS list
    ebs_volumes.py
    ebs_snapshots.py
    elastic_ips.py
    load_balancers.py
    nat_gateways.py
    ec2_stopped.py
    iam_keys.py
    security_groups.py
    log_groups.py
```

Each module exposes exactly one public function:

```python
def detect(snapshot: Snapshot, config: Config) -> list[Tombstone]:
    ...
```

Rules enforced by tests:
- Must not modify any field of `snapshot`.
- Must return an empty list (not raise) when the relevant snapshot key is empty.
- All returned Tombstones must pass the Pydantic model validator.
- Running twice on the same snapshot must return an identical list (deterministic).

---

## 7. Pricing Module

`scanner/pricing.py` reads `scanner/pricing.json` at import time. The JSON file has a `last_updated` date header and per-resource-type unit prices (e.g. `gp2_per_gb_month`, `eip_per_hour`, `nat_per_hour`, `nat_per_gb`). Cost estimates are calculated from resource metadata (size, age, etc.) and stored in each Tombstone.

Pricing JSON structure:
```jsonc
{
  "last_updated": "2025-01-01",
  "region_multipliers": { "ap-southeast-1": 1.08, ... },
  "prices": {
    "ebs_gp2_per_gb_month":    0.10,
    "ebs_gp3_per_gb_month":    0.08,
    "ebs_io1_per_gb_month":    0.125,
    "eip_unassociated_per_hr": 0.005,
    "nat_per_hr":              0.045,
    "nat_per_gb":              0.045,
    "alb_per_hr":              0.008,
    "nlb_per_hr":              0.006,
    "cw_logs_per_gb_month":    0.03
  }
}
```

All costs labelled "estimated" in the report and UI. Pricing is verified against AWS Pricing MCP server during development; the file carries a `last_updated` date so users know when to refresh it.

---

## 8. IAM Read-Only Policy

Stored at `infra/iam-policy.json` and reproduced verbatim in `README.md` and the About view.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "GraveyardShiftReadOnly",
      "Effect": "Allow",
      "Action": [
        "ec2:DescribeVolumes",
        "ec2:DescribeSnapshots",
        "ec2:DescribeAddresses",
        "ec2:DescribeInstances",
        "ec2:DescribeNatGateways",
        "ec2:DescribeSecurityGroups",
        "ec2:DescribeNetworkInterfaces",
        "ec2:DescribeRegions",
        "elasticloadbalancing:DescribeLoadBalancers",
        "elasticloadbalancing:DescribeTargetGroups",
        "elasticloadbalancing:DescribeTargetHealth",
        "cloudwatch:GetMetricStatistics",
        "logs:DescribeLogGroups",
        "logs:DescribeMetricFilters",
        "logs:FilterLogEvents",
        "iam:ListUsers",
        "iam:ListAccessKeys",
        "iam:GetAccessKeyLastUsed"
      ],
      "Resource": "*"
    }
  ]
}
```

No `Deny` stanza needed; the policy grants only the minimum reads. Users attach this as a managed policy to their scanner IAM role or user.

---

## 9. Static Hosting Design (Netlify — no AWS resources, no cost)

The web app is a fully static Vite build. No CDK, no CloudFormation, no S3, no CloudFront stack is deployed. This avoids all AWS costs.

### Primary: Netlify free tier

**`netlify.toml`** at the repo root:
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

Deploy command: `netlify deploy --prod --dir web/dist`
Netlify provides HTTPS automatically on its CDN with no configuration.

### Fallback: GitHub Pages

`make deploy-pages` runs `npx gh-pages -d web/dist`.
GitHub Pages serves HTTPS on `<user>.github.io/<repo>`.
SPA routing requires a `404.html` redirect trick; Vite build step produces this.

### IAM policy artifact

`infra/iam-policy.json` is a static JSON file (no CDK, no CloudFormation). Users download it and attach it to their scanner IAM role manually. The `infra/` directory contains only this file and the README reference — no CDK app, no `cdk.json`, no TypeScript.

---

## 10. Web App Architecture

```
web/src/
    main.tsx                 # Vite entry
    App.tsx                  # Router + layout
    store/
        reportStore.ts       # Zustand store: loaded report, active view
    views/
        Graveyard.tsx        # SVG/CSS graveyard scene
        Crypt.tsx            # sortable/filterable table
        Exorcism.tsx         # cleanup plan list
        About.tsx            # static content
    components/
        Tombstone.tsx        # individual tombstone shape + tooltip
        HeadlineBar.tsx      # summary stats
        SeverityBadge.tsx    # text + colour chip
        CopyButton.tsx       # clipboard utility
        FileDropZone.tsx     # drag-and-drop report loader
        SampleDataBanner.tsx # shown when demo:true
    hooks/
        useReport.ts         # loads and validates report JSON
        useFilter.ts         # filter/sort state for Crypt
    utils/
        schema.ts            # ajv instance + validate()
        escape.ts            # HTML-safe string rendering helper
        cost.ts              # format Decimal as "$X.XX/mo (estimated)"
    assets/
        demo-report.json     # bundled seed report
        moon.svg             # licence-clear SVG
        fog.svg              # licence-clear SVG (or CSS-only fog)
```

**State management:** Zustand (lightweight, no boilerplate). The store holds the active `Report | null` and the current view name. All filtering/sorting state is local to `Crypt.tsx` via `useFilter`.

**Routing:** `react-router-dom` with hash routing (no server-side routing config needed; works with Netlify's redirect rule and GitHub Pages).

**Schema validation in-browser:** `ajv` with the JSON Schema compiled at build time and imported as a module.

---

## 11. Error Handling and Logging

### Scanner

| Situation | Behaviour |
|-----------|-----------|
| AWS credential error | Log error, exit 1 |
| Single region auth failure | Log warning, skip region, exit 2 at end |
| Paginator / API throttle | Retry with exponential backoff (boto3 default) up to 3 retries |
| Detector exception | Log error with region + resource context, skip that resource, continue |
| Schema validation failure on output | Log error, exit 3 |
| `--demo` with bad seed file | Log error, exit 1 |

Log levels: `DEBUG` for API call details, `INFO` for progress milestones, `WARNING` for skipped regions/resources, `ERROR` for failures. Default level: `INFO`. `--verbose` sets `DEBUG`.

Credentials and full ARNs are never emitted at INFO or below.

### Web App

| Situation | Behaviour |
|-----------|-----------|
| Bundled demo report fails schema | Compile-time error (caught in CI/`make test`) |
| User-dropped file fails schema | Toast error; previous report retained |
| User-dropped file is not valid JSON | Toast error; previous report retained |
| Resource name/value contains HTML | Escaped by React's default renderer; `dangerouslySetInnerHTML` banned |

---

## 12. Correctness Properties for Property-Based Tests

These properties are suitable for Hypothesis (Python) or manual parameterised pytest tests.

| # | Property | Test approach |
|---|-----------|---------------|
| P1 | Detectors never mutate the input Snapshot | Deep-copy snapshot before calling detect; assert equal after |
| P2 | Every Tombstone has `estimated_monthly_cost >= 0` | Assert on all items in returned list |
| P3 | Running detect twice on the same snapshot returns an identical list | Call twice, assert `==` |
| P4 | Report with N tombstones has `summary.total_tombstones == N` | Parameterise over random tombstone lists |
| P5 | `summary.estimated_monthly_cost == sum(t.estimated_monthly_cost for t in tombstones)` | Same |
| P6 | `summary.undead_credentials_count == len([t for t in tombstones if t.resource_type == "IAM::AccessKey"])` | Same |
| P7 | Every report output validates against `schema/report.schema.json` | Validate in `report.py` before write; also in `make test` for seed report |
| P8 | Detectors return an empty list (not raise) on an empty Snapshot | Parameterise with zero-resource snapshots for all 9 detectors |
| P9 | No detector flags the `default` security group | Inject a snapshot with only a default SG; assert empty list |
| P10 | Demo mode produces a report with `demo: true` | Assert on report metadata |
| P11 | Tombstone `exorcism_cli` contains the `resource_id` of that Tombstone | Assert substring for all tombstones |
| P12 | `by_severity` counts sum to `total_tombstones` | Assert on summary |

---

## 13. Directory Layout

```
graveyard-shift/
├── .kiro/
│   ├── steering/          # product, tech, design, security rules
│   ├── specs/
│   │   └── graveyard-shift/
│   │       ├── requirements.md
│   │       ├── design.md
│   │       ├── tasks.md
│   │       └── automation-proposal.md
│   ├── hooks/             # (created in M4 or on approval)
│   └── settings/
│       └── mcp.json       # (configured on approval)
├── schema/
│   └── report.schema.json
├── scanner/
│   ├── __init__.py
│   ├── cli.py             # click entry point
│   ├── fetcher.py
│   ├── models.py
│   ├── pricing.py
│   ├── pricing.json
│   ├── config.py
│   ├── report.py
│   └── detectors/
│       └── (9 modules)
├── seed/
│   ├── snapshot.json
│   └── report.json
├── web/
│   ├── index.html
│   ├── vite.config.ts
│   ├── src/
│   └── …
├── infra/
│   └── iam-policy.json    # static JSON only — no CDK, no CloudFormation
├── demo/
│   └── DEMO_SCRIPT.md
├── tests/
│   ├── conftest.py
│   └── detectors/
│       └── (9 test modules)
├── netlify.toml           # Netlify deploy config (free tier, no AWS)
├── Makefile
├── pyproject.toml
└── README.md
```
