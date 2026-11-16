"""Tests for scanner.detectors.ec2_stopped"""

from __future__ import annotations

import copy
from datetime import UTC, datetime, timedelta

from scanner.detectors.ec2_stopped import detect
from scanner.models import Severity, Snapshot

SCAN_TIME = datetime(2025, 7, 1, 10, 0, 0, tzinfo=UTC)
ACCOUNT = "111122223333"
REGION = "us-east-1"


def make_snapshot(instances: list[dict], volumes: list[dict] | None = None) -> Snapshot:
    return Snapshot(
        account_id=ACCOUNT,
        regions=[REGION],
        scanned_at=SCAN_TIME,
        instances={REGION: instances},
        volumes={REGION: volumes or []},
    )


def stopped_instance(
    inst_id: str = "i-0dead000000000001",
    stopped_days_ago: int = 45,
    name: str | None = "old-staging",
    inst_type: str = "t3.medium",
    vol_ids: list[str] | None = None,
) -> dict:
    stop_time = SCAN_TIME - timedelta(days=stopped_days_ago)
    stop_str = stop_time.strftime("%Y-%m-%d %H:%M:%S")
    tags = [{"Key": "Name", "Value": name}] if name else []
    bdm = [{"Ebs": {"VolumeId": vid}} for vid in (vol_ids or [])]
    return {
        "InstanceId": inst_id,
        "InstanceType": inst_type,
        "State": {"Name": "stopped"},
        "StateTransitionReason": f"User initiated ({stop_str} GMT)",
        "LaunchTime": (SCAN_TIME - timedelta(days=stopped_days_ago + 10)).isoformat(),
        "Tags": tags,
        "BlockDeviceMappings": bdm,
    }


def running_instance(inst_id: str = "i-0live000000000001") -> dict:
    return {
        "InstanceId": inst_id,
        "InstanceType": "c5.xlarge",
        "State": {"Name": "running"},
        "StateTransitionReason": "",
        "LaunchTime": (SCAN_TIME - timedelta(days=10)).isoformat(),
        "Tags": [],
        "BlockDeviceMappings": [],
    }


def vol(vol_id: str, size: int = 100) -> dict:
    return {
        "VolumeId": vol_id,
        "Size": size,
        "VolumeType": "gp2",
        "State": "in-use",
        "CreateTime": "2025-01-01T00:00:00Z",
        "AvailabilityZone": "us-east-1a",
        "Tags": [],
    }


# ── Positive ──────────────────────────────────────────────────────────────────


def test_instance_stopped_45_days_is_flagged(default_config):
    inst = stopped_instance(stopped_days_ago=45, vol_ids=["vol-0abc"])
    volumes = [vol("vol-0abc", size=50)]
    snap = make_snapshot([inst], volumes)
    result = detect(snap, default_config)
    assert len(result) == 1
    t = result[0]
    assert t.resource_id == "i-0dead000000000001"
    assert t.cause == "dead but still billed for EBS"
    assert t.severity == Severity.WASTEFUL
    assert t.resource_type == "EC2::Instance"
    assert t.metadata["instance_type"] == "t3.medium"
    assert t.metadata["ebs_size_gib"] == 50
    assert t.estimated_monthly_cost >= 0
    assert "--dry-run" in t.exorcism_cli
    assert "i-0dead000000000001" in t.exorcism_cli


def test_instance_stopped_exactly_30_days_is_flagged(default_config):
    inst = stopped_instance(stopped_days_ago=30)
    result = detect(make_snapshot([inst]), default_config)
    assert len(result) == 1


# ── Negative ──────────────────────────────────────────────────────────────────


def test_instance_stopped_10_days_not_flagged(default_config):
    inst = stopped_instance(stopped_days_ago=10)
    result = detect(make_snapshot([inst]), default_config)
    assert result == []


def test_running_instance_not_flagged(default_config):
    result = detect(make_snapshot([running_instance()]), default_config)
    assert result == []


def test_empty_snapshot_returns_empty(default_config, empty_snapshot):
    result = detect(empty_snapshot, default_config)
    assert result == []


# ── Edge ──────────────────────────────────────────────────────────────────────


def test_unparseable_state_reason_falls_back_to_launch_time(default_config):
    """When StateTransitionReason has no parseable timestamp, LaunchTime is used."""
    inst = stopped_instance(stopped_days_ago=45)
    inst["StateTransitionReason"] = "Client.InstanceInitiatedShutdown"
    # LaunchTime is 55 days ago (stopped_days_ago + 10)
    result = detect(make_snapshot([inst]), default_config)
    # Falls back to LaunchTime which is 55 days → should be flagged
    assert len(result) == 1


def test_zero_ebs_cost_non_negative(default_config):
    """An instance with no volumes: cost is 0, not negative."""
    inst = stopped_instance(stopped_days_ago=45, vol_ids=[])
    result = detect(make_snapshot([inst], []), default_config)
    assert len(result) == 1
    assert result[0].estimated_monthly_cost >= 0


# ── Property tests ────────────────────────────────────────────────────────────


def test_snapshot_not_mutated(default_config):
    inst = stopped_instance(stopped_days_ago=45)
    snap = make_snapshot([inst])
    before = copy.deepcopy(snap)
    detect(snap, default_config)
    assert snap.instances == before.instances


def test_deterministic(default_config):
    instances = [stopped_instance(f"i-{i:020d}", stopped_days_ago=45) for i in range(3)]
    snap = make_snapshot(instances)
    r1 = detect(snap, default_config)
    r2 = detect(snap, default_config)
    assert [t.resource_id for t in r1] == [t.resource_id for t in r2]


def test_cost_non_negative(default_config):
    instances = [stopped_instance(f"i-{i:020d}", stopped_days_ago=45) for i in range(3)]
    snap = make_snapshot(instances)
    for t in detect(snap, default_config):
        assert t.estimated_monthly_cost >= 0
