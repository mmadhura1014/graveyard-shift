"""Tests for scanner.detectors.security_groups"""

from __future__ import annotations

import copy
from datetime import UTC, datetime
from decimal import Decimal

from scanner.detectors.security_groups import detect
from scanner.models import Severity, Snapshot

SCAN_TIME = datetime(2025, 7, 1, 10, 0, 0, tzinfo=UTC)
ACCOUNT = "111122223333"
REGION = "us-east-1"


def make_snapshot(
    sgs: list[dict],
    enis: list[dict] | None = None,
    instances: list[dict] | None = None,
    lbs: list[dict] | None = None,
) -> Snapshot:
    return Snapshot(
        account_id=ACCOUNT,
        regions=[REGION],
        scanned_at=SCAN_TIME,
        security_groups={REGION: sgs},
        enis={REGION: enis or []},
        instances={REGION: instances or []},
        load_balancers={REGION: lbs or []},
    )


def sg(
    group_id: str = "sg-0dead000000000001", name: str = "orphan-sg", vpc_id: str = "vpc-0abc"
) -> dict:
    return {
        "GroupId": group_id,
        "GroupName": name,
        "VpcId": vpc_id,
        "Description": "test sg",
        "Tags": [{"Key": "Name", "Value": name}],
    }


def default_sg(group_id: str = "sg-0default0000001") -> dict:
    return {
        "GroupId": group_id,
        "GroupName": "default",
        "VpcId": "vpc-0abc",
        "Description": "default VPC security group",
        "Tags": [],
    }


def eni_using(group_id: str) -> dict:
    return {"NetworkInterfaceId": "eni-0001", "Groups": [{"GroupId": group_id}], "Status": "in-use"}


def instance_using(group_id: str) -> dict:
    return {
        "InstanceId": "i-0001",
        "InstanceType": "t3.small",
        "State": {"Name": "running"},
        "StateTransitionReason": "",
        "LaunchTime": "2025-01-01T00:00:00Z",
        "SecurityGroups": [{"GroupId": group_id}],
        "Tags": [],
        "BlockDeviceMappings": [],
    }


# ── Positive ──────────────────────────────────────────────────────────────────


def test_unattached_sg_is_flagged(default_config):
    snap = make_snapshot([sg()])
    result = detect(snap, default_config)
    assert len(result) == 1
    t = result[0]
    assert t.resource_id == "sg-0dead000000000001"
    assert t.cause == "forgotten"
    assert t.severity == Severity.HARMLESS
    assert t.resource_type == "EC2::SecurityGroup"
    assert t.estimated_monthly_cost == Decimal("0")
    assert "--dry-run" in t.exorcism_cli
    assert "sg-0dead000000000001" in t.exorcism_cli


def test_multiple_orphaned_sgs(default_config):
    sgs = [sg(f"sg-dead{i:015d}", f"orphan-{i}") for i in range(3)]
    result = detect(make_snapshot(sgs), default_config)
    assert len(result) == 3


# ── Negative ──────────────────────────────────────────────────────────────────


def test_sg_attached_to_eni_not_flagged(default_config):
    group_id = "sg-0live000000000001"
    snap = make_snapshot([sg(group_id)], enis=[eni_using(group_id)])
    result = detect(snap, default_config)
    assert result == []


def test_sg_attached_to_instance_not_flagged(default_config):
    group_id = "sg-0live000000000002"
    snap = make_snapshot([sg(group_id)], instances=[instance_using(group_id)])
    result = detect(snap, default_config)
    assert result == []


def test_sg_attached_to_lb_not_flagged(default_config):
    group_id = "sg-0live000000000003"
    lb = {
        "LoadBalancerArn": "arn:aws:...",
        "LoadBalancerName": "my-lb",
        "Type": "application",
        "SecurityGroups": [group_id],
        "State": {"Code": "active"},
        "DNSName": "x.elb.amazonaws.com",
    }
    snap = make_snapshot([sg(group_id)], lbs=[lb])
    result = detect(snap, default_config)
    assert result == []


def test_default_sg_not_flagged(default_config):
    snap = make_snapshot([default_sg()])
    result = detect(snap, default_config)
    assert result == []


def test_empty_sg_list_returns_empty(default_config, empty_snapshot):
    result = detect(empty_snapshot, default_config)
    assert result == []


# ── Edge ──────────────────────────────────────────────────────────────────────


def test_empty_eni_and_instance_lists_flags_non_default(default_config):
    snap = make_snapshot([sg(), default_sg()], enis=[], instances=[])
    result = detect(snap, default_config)
    assert len(result) == 1  # only the non-default one
    assert result[0].resource_id == "sg-0dead000000000001"


# ── Property tests ────────────────────────────────────────────────────────────


def test_snapshot_not_mutated(default_config):
    snap = make_snapshot([sg()])
    before = copy.deepcopy(snap)
    detect(snap, default_config)
    assert snap.security_groups == before.security_groups


def test_deterministic(default_config):
    sgs = [sg(f"sg-dead{i:015d}") for i in range(3)]
    snap = make_snapshot(sgs)
    r1 = detect(snap, default_config)
    r2 = detect(snap, default_config)
    assert [t.resource_id for t in r1] == [t.resource_id for t in r2]


def test_cost_always_zero(default_config):
    sgs = [sg(f"sg-dead{i:015d}") for i in range(3)]
    for t in detect(make_snapshot(sgs), default_config):
        assert t.estimated_monthly_cost == Decimal("0")
