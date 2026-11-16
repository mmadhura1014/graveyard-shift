# Graveyard Shift

Find forgotten AWS resources and see each one as a tombstone with its cause of death and a safe cleanup plan.

Built for **Kiroween 2026** (Costume Contest category), using Kiro specs, steering files, agent hooks and MCP servers. See [`/.kiro`](.kiro).

A read-only scanner finds idle, orphaned and abandoned AWS resources (unattached EBS volumes, idle NAT gateways, stale IAM keys, ...). A web app shows them as a haunted graveyard. **It never deletes anything.** The "Exorcism" view only generates commands that you review and run yourself.

## Try it in two commands (no AWS account needed)

```bash
make setup      # Python venv + web dependencies
make demo       # scan the bundled SAMPLE account, write a report
```

Then view the graveyard:

```bash
cd web && npm run dev     # open the printed local URL
```

The web app loads a bundled sample report by default (labelled "Sample Data"). You can also drop your own `report.json` onto the page. It is processed locally in your browser and never uploaded.

## What it detects

| Resource | Cause of death |
|---|---|
| Unattached EBS volume | abandoned |
| EBS snapshot whose source volume is gone | orphaned |
| Unassociated Elastic IP | idle |
| Load balancer with no targets / no traffic | lonely |
| NAT gateway with ~no traffic | idle |
| EC2 instance stopped for 30+ days | dead but still billed for EBS |
| IAM access key unused 90+ days | undead credential |
| Security group attached to nothing | forgotten |
| CloudWatch log group with no retention | hoarder |

Thresholds live in one config file. Costs are **estimates** from a bundled, dated price table (`scanner/pricing.json`), not billing data.

## Scanning a real account

```bash
.venv/bin/graveyard scan --profile YOUR_PROFILE --regions us-east-1,eu-west-1 --out report.json
```

Use a profile that carries read-only permissions (Describe*/List*/Get*, CloudWatch `GetMetricStatistics`/`GetMetricData`). Note that API calls appear in your CloudTrail. Only scan accounts you are allowed to scan.

## How it was verified (honest notes)

- **Unit and property tests** cover every detector: `make test`.
- **The live AWS code path was tested only against [moto](https://github.com/getmoto/moto)**, an in-process AWS mock with fake credentials (`make demo-live`). **It has not been run against a real AWS account.**
- moto does not produce CloudWatch metric datapoints, so the traffic-based NAT gateway and load balancer checks are covered by fixture-based unit tests, not by the moto test.
- All numbers in the bundled demo are **synthetic sample data**, not measurements from a real account.

## Layout

```
scanner/   Python 3.12 CLI + one module per detector
schema/    JSON Schema for report.json
seed/      synthetic sample account + expected report
web/       Vite + React + TypeScript static app
tests/     pytest suite (incl. moto integration test)
.kiro/     steering, specs, hooks, MCP config used to build this
```

## Development

```bash
make test       # Python + web tests
make lint       # ruff + eslint
make demo-live  # real fetcher against a mocked account
```

## License

MIT. See [LICENSE](LICENSE).
