"""
Property-based tests (P1–P12) for Graveyard Shift.

Covers the correctness properties defined in design.md §12.
Uses pytest.mark.parametrize for deterministic cases and Hypothesis
for generative cases where applicable.
"""

from __future__ import annotations

import copy
import json
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import pytest

from scanner.config import DEFAULT_CONFIG
from scanner.detectors import ALL_DETECTORS
from scanner.models import ReportSummary, Severity, Snapshot, Tombstone

SCHEMA_PATH = Path("schema/report.schema.json")
SEED_REPORT = Path("seed/report.json")
SCAN_TIME = datetime(2025, 7, 1, 10, 0, 0, tzinfo=UTC)
ACCOUNT = "111122223333"


# ── Helpers ───────────────────────────────────────────────────────────────────


def make_tombstone(**kwargs) -> Tombstone:
    defaults = {
        "resource_id": "res-001",
        "resource_name": "test",
        "resource_type": "EC2::Volume",
        "region": "us-east-1",
        "account_id": ACCOUNT,
        "cause": "abandoned",
        "severity": Severity.WASTEFUL,
        "detected_at": SCAN_TIME,
        "estimated_monthly_cost": Decimal("10.00"),
        "metadata": {},
        "exorcism_cli": "aws ec2 delete-volume --volume-id res-001 --region us-east-1 --dry-run",
        "exorcism_tf": 'resource "aws_ebs_volume" "res_001" {}',
    }
    defaults.update(kwargs)
    return Tombstone(**defaults)


def empty_snap() -> Snapshot:
    return Snapshot(account_id=ACCOUNT, regions=["us-east-1"], scanned_at=SCAN_TIME)


# ── P1: detectors never mutate the input Snapshot ─────────────────────────────


@pytest.mark.parametrize(
    "detector", ALL_DETECTORS, ids=[d.__module__.split(".")[-1] for d in ALL_DETECTORS]
)
def test_P1_detector_does_not_mutate_snapshot(detector, seed_snapshot):
    before = copy.deepcopy(seed_snapshot)
    detector(seed_snapshot, DEFAULT_CONFIG)
    assert seed_snapshot.volumes == before.volumes
    assert seed_snapshot.snapshots_data == before.snapshots_data
    assert seed_snapshot.elastic_ips == before.elastic_ips
    assert seed_snapshot.load_balancers == before.load_balancers
    assert seed_snapshot.nat_gateways == before.nat_gateways
    assert seed_snapshot.instances == before.instances
    assert seed_snapshot.security_groups == before.security_groups
    assert seed_snapshot.enis == before.enis
    assert seed_snapshot.log_groups == before.log_groups
    assert seed_snapshot.iam_access_keys == before.iam_access_keys
    assert seed_snapshot.account_id == before.account_id


# ── P2: every Tombstone has estimated_monthly_cost >= 0 ───────────────────────


@pytest.mark.parametrize(
    "detector", ALL_DETECTORS, ids=[d.__module__.split(".")[-1] for d in ALL_DETECTORS]
)
def test_P2_all_tombstone_costs_non_negative(detector, seed_snapshot):
    results = detector(seed_snapshot, DEFAULT_CONFIG)
    for t in results:
        assert t.estimated_monthly_cost >= 0, (
            f"{detector.__module__}: tombstone {t.resource_id} has cost {t.estimated_monthly_cost}"
        )


# ── P3: running detect twice returns identical lists ──────────────────────────


@pytest.mark.parametrize(
    "detector", ALL_DETECTORS, ids=[d.__module__.split(".")[-1] for d in ALL_DETECTORS]
)
def test_P3_detector_is_deterministic(detector, seed_snapshot):
    r1 = detector(seed_snapshot, DEFAULT_CONFIG)
    r2 = detector(seed_snapshot, DEFAULT_CONFIG)
    assert [t.resource_id for t in r1] == [t.resource_id for t in r2]
    assert [t.cause for t in r1] == [t.cause for t in r2]


# ── P4: summary.total_tombstones == len(tombstones) ───────────────────────────


@pytest.mark.parametrize("n", [0, 1, 5, 20])
def test_P4_summary_total_matches_list_length(n):
    tombstones = [
        make_tombstone(
            resource_id=f"res-{i:03d}",
            exorcism_cli=f"aws ec2 delete-volume --volume-id res-{i:03d} --dry-run",
        )
        for i in range(n)
    ]
    summary = ReportSummary.from_tombstones(tombstones)
    assert summary.total_tombstones == n


# ── P5: summary.estimated_monthly_cost == sum of tombstone costs ──────────────


@pytest.mark.parametrize(
    "costs",
    [
        [Decimal("0")],
        [Decimal("10.00"), Decimal("20.00"), Decimal("3.65")],
        [Decimal("0"), Decimal("0"), Decimal("0")],
    ],
)
def test_P5_summary_cost_equals_sum(costs):
    tombstones = [
        make_tombstone(
            resource_id=f"res-{i:03d}",
            estimated_monthly_cost=c,
            exorcism_cli=f"aws ec2 delete-volume --volume-id res-{i:03d} --dry-run",
        )
        for i, c in enumerate(costs)
    ]
    summary = ReportSummary.from_tombstones(tombstones)
    assert summary.estimated_monthly_cost == sum(costs)


# ── P6: undead_credentials_count == IAM::AccessKey tombstone count ────────────


def test_P6_undead_credentials_count():
    tombstones = [
        make_tombstone(
            resource_id="k1",
            resource_type="IAM::AccessKey",
            region="global",
            cause="undead credentials",
            severity=Severity.RISKY,
            estimated_monthly_cost=Decimal("0"),
            exorcism_cli="aws iam delete-access-key --access-key-id k1 --user-name u",
        ),
        make_tombstone(
            resource_id="k2",
            resource_type="IAM::AccessKey",
            region="global",
            cause="undead credentials",
            severity=Severity.RISKY,
            estimated_monthly_cost=Decimal("0"),
            exorcism_cli="aws iam delete-access-key --access-key-id k2 --user-name u",
        ),
        make_tombstone(
            resource_id="v1",
            resource_type="EC2::Volume",
            exorcism_cli="aws ec2 delete-volume --volume-id v1 --dry-run",
        ),
    ]
    summary = ReportSummary.from_tombstones(tombstones)
    assert summary.undead_credentials_count == 2


# ── P7: every report output validates against the JSON Schema ─────────────────


def test_P7_seed_report_validates_against_schema():
    import jsonschema

    schema = json.loads(SCHEMA_PATH.read_text())
    report = json.loads(SEED_REPORT.read_text())
    jsonschema.validate(report, schema)


def test_P7_full_scan_report_validates_against_schema(seed_snapshot):
    import jsonschema

    from scanner.report import _report_to_dict, build_report

    tombstones = []
    for detector in ALL_DETECTORS:
        tombstones.extend(detector(seed_snapshot, DEFAULT_CONFIG))
    report = build_report(
        tombstones=tombstones,
        snapshot=seed_snapshot,
        scan_duration=0.5,
        demo=True,
    )
    schema = json.loads(SCHEMA_PATH.read_text())
    jsonschema.validate(_report_to_dict(report), schema)


# ── P8: detectors return [] (not raise) on empty Snapshot ─────────────────────


@pytest.mark.parametrize(
    "detector", ALL_DETECTORS, ids=[d.__module__.split(".")[-1] for d in ALL_DETECTORS]
)
def test_P8_empty_snapshot_returns_empty_list(detector):
    result = detector(empty_snap(), DEFAULT_CONFIG)
    assert result == [], f"{detector.__module__} raised or returned non-empty on empty snapshot"


# ── P9: security groups detector never flags the default SG ───────────────────


def test_P9_default_sg_never_flagged():
    from scanner.detectors.security_groups import detect

    snap = Snapshot(
        account_id=ACCOUNT,
        regions=["us-east-1"],
        scanned_at=SCAN_TIME,
        security_groups={
            "us-east-1": [
                {
                    "GroupId": "sg-default01",
                    "GroupName": "default",
                    "VpcId": "vpc-001",
                    "Description": "default",
                    "Tags": [],
                },
            ]
        },
    )
    result = detect(snap, DEFAULT_CONFIG)
    assert result == []


# ── P10: demo mode produces report with demo=True ─────────────────────────────


def test_P10_demo_report_has_demo_true():
    report = json.loads(SEED_REPORT.read_text())
    assert report["demo"] is True


# ── P11: exorcism_cli contains the resource_id ────────────────────────────────


@pytest.mark.parametrize(
    "detector", ALL_DETECTORS, ids=[d.__module__.split(".")[-1] for d in ALL_DETECTORS]
)
def test_P11_exorcism_cli_contains_resource_id(detector, seed_snapshot):
    results = detector(seed_snapshot, DEFAULT_CONFIG)
    for t in results:
        assert t.resource_id in t.exorcism_cli, (
            f"{detector.__module__}: exorcism_cli for {t.resource_id!r} "
            f"does not contain the resource_id.\ncli={t.exorcism_cli!r}"
        )


# ── P12: by_severity counts sum to total_tombstones ──────────────────────────


@pytest.mark.parametrize(
    "severities",
    [
        [Severity.HARMLESS],
        [Severity.WASTEFUL, Severity.WASTEFUL, Severity.RISKY],
        [Severity.HARMLESS, Severity.WASTEFUL, Severity.RISKY],
        [],
    ],
)
def test_P12_by_severity_sums_to_total(severities):
    tombstones = [
        make_tombstone(
            resource_id=f"r{i}",
            severity=s,
            exorcism_cli=f"aws ec2 delete-volume --volume-id r{i} --dry-run",
        )
        for i, s in enumerate(severities)
    ]
    summary = ReportSummary.from_tombstones(tombstones)
    sev_sum = sum(summary.by_severity.values())
    assert sev_sum == summary.total_tombstones
