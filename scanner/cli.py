"""
Graveyard Shift — CLI entry point.

Commands:
    graveyard scan [--demo] [--profile X] [--regions a,b] [--out path] [--config path] [--verbose]
"""

from __future__ import annotations

import json
import logging
import sys
import time
from datetime import datetime
from pathlib import Path

import click

from scanner.config import load_config
from scanner.detectors import ALL_DETECTORS
from scanner.models import Snapshot
from scanner.report import build_report, write_report

_SEED_SNAPSHOT = Path(__file__).parent.parent / "seed" / "snapshot.json"

log = logging.getLogger("graveyard")


@click.group()
def main() -> None:
    """Graveyard Shift — find zombie AWS resources haunting your account."""


@main.command()
@click.option(
    "--demo", is_flag=True, default=False, help="Run against bundled seed data (no AWS calls)."
)
@click.option("--profile", default=None, metavar="PROFILE", help="AWS named profile to use.")
@click.option(
    "--regions",
    default=None,
    metavar="REGIONS",
    help="Comma-separated list of AWS regions (e.g. us-east-1,eu-west-1).",
)
@click.option(
    "--out",
    default="report.json",
    metavar="PATH",
    help="Output path for the report JSON (default: report.json).",
)
@click.option(
    "--config",
    "config_path",
    default=None,
    metavar="PATH",
    help="Path to a TOML config file for threshold overrides.",
)
@click.option("--verbose", is_flag=True, default=False, help="Enable DEBUG logging.")
def scan(
    demo: bool,
    profile: str | None,
    regions: str | None,
    out: str,
    config_path: str | None,
    verbose: bool,
) -> None:
    """Scan for zombie AWS resources and write a report."""
    _setup_logging(verbose)

    # Load thresholds
    cfg_file = Path(config_path) if config_path else None
    config = load_config(cfg_file)

    if demo:
        if profile or regions:
            log.warning("--profile and --regions are ignored in --demo mode.")
        _run_demo(out=Path(out), config=config)
    else:
        _run_live(
            profile=profile,
            regions=regions,
            out=Path(out),
            config=config,
        )


def _run_demo(out: Path, config: dict) -> None:
    """Load seed snapshot, run detectors, write report."""
    log.info("Demo mode: loading seed snapshot from %s", _SEED_SNAPSHOT)

    if not _SEED_SNAPSHOT.exists():
        click.echo(f"Error: seed snapshot not found at {_SEED_SNAPSHOT}", err=True)
        sys.exit(1)

    raw = json.loads(_SEED_SNAPSHOT.read_text())
    snapshot = _snapshot_from_dict(raw)

    t0 = time.monotonic()
    tombstones = []
    for detector in ALL_DETECTORS:
        try:
            found = detector(snapshot, config)
            log.debug("%s found %d tombstones", detector.__module__, len(found))
            tombstones.extend(found)
        except Exception as exc:
            log.error("Detector %s failed: %s", detector.__module__, exc)

    duration = time.monotonic() - t0

    report = build_report(
        tombstones=tombstones,
        snapshot=snapshot,
        scan_duration=duration,
        demo=True,
    )
    write_report(report, out)

    click.echo(f"✓ Graveyard Shift demo report written to {out}")
    click.echo(f"  Tombstones: {report.summary.total_tombstones}")
    click.echo(
        f"  Estimated haunting cost: ${report.summary.estimated_monthly_cost:.2f}/mo (estimated)"
    )
    click.echo(f"  Undead credentials: {report.summary.undead_credentials_count}")


def _run_live(
    profile: str | None,
    regions: str | None,
    out: Path,
    config: dict,
) -> None:
    """Fetch live AWS data and produce a report."""
    try:
        import boto3
    except ImportError:
        click.echo("Error: boto3 is required for live scanning.", err=True)
        sys.exit(1)

    try:
        from scanner.fetcher import fetch
    except ImportError:
        click.echo("Error: fetcher not yet implemented — use --demo.", err=True)
        sys.exit(1)

    session_kwargs: dict = {}
    if profile:
        session_kwargs["profile_name"] = profile

    try:
        session = boto3.Session(**session_kwargs)
    except Exception as e:
        log.error("Failed to create AWS session: %s", e)
        sys.exit(1)

    region_list = [r.strip() for r in regions.split(",")] if regions else None

    exit_code = 0
    t0 = time.monotonic()
    snapshot, skip_count = fetch(session=session, regions=region_list, config=config)
    if skip_count > 0:
        exit_code = 2  # partial failure — some regions skipped

    tombstones = []
    for detector in ALL_DETECTORS:
        try:
            tombstones.extend(detector(snapshot, config))
        except Exception as exc:
            log.error("Detector %s failed: %s", detector.__module__, exc)

    duration = time.monotonic() - t0
    report = build_report(
        tombstones=tombstones,
        snapshot=snapshot,
        scan_duration=duration,
        demo=False,
    )
    write_report(report, out)

    click.echo(f"✓ Graveyard Shift report written to {out}")
    click.echo(f"  Tombstones: {report.summary.total_tombstones}")
    click.echo(
        f"  Estimated haunting cost: ${report.summary.estimated_monthly_cost:.2f}/mo (estimated)"
    )
    click.echo(f"  Undead credentials: {report.summary.undead_credentials_count}")

    if exit_code != 0:
        sys.exit(exit_code)


def _setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(levelname)s  %(name)s  %(message)s",
    )
    # Never log at INFO or below for boto3/botocore (may contain sensitive data)
    logging.getLogger("boto3").setLevel(logging.WARNING)
    logging.getLogger("botocore").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)


def _snapshot_from_dict(raw: dict) -> Snapshot:
    """Deserialise a seed snapshot dict into a Snapshot dataclass."""
    return Snapshot(
        account_id=raw["account_id"],
        regions=raw["regions"],
        scanned_at=datetime.fromisoformat(raw["scanned_at"].replace("Z", "+00:00")),
        volumes=raw.get("volumes", {}),
        snapshots_data=raw.get("snapshots_data", {}),
        elastic_ips=raw.get("elastic_ips", {}),
        load_balancers=raw.get("load_balancers", {}),
        target_groups=raw.get("target_groups", {}),
        target_health=raw.get("target_health", {}),
        nat_gateways=raw.get("nat_gateways", {}),
        instances=raw.get("instances", {}),
        security_groups=raw.get("security_groups", {}),
        enis=raw.get("enis", {}),
        log_groups=raw.get("log_groups", {}),
        cw_metrics=raw.get("cw_metrics", {}),
        iam_users=raw.get("iam_users", []),
        iam_access_keys=raw.get("iam_access_keys", []),
    )
