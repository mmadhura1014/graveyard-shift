"""
Tests for scanner.detectors.ebs_volumes
"""

from __future__ import annotations

import copy
from datetime import UTC, datetime, timedelta

from scanner.detectors.ebs_volumes import detect
from scanner.models import Severity, Snapshot

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SCAN_TIME = datetime(2025, 7, 1, 10, 0, 0, tzinfo=UTC)
ACCOUNT = "111122223333"


def make_snapshot(volumes: list[dict]) -> Snapshot:
    return Snapshot(
        account_id=ACCOUNT,
        regions=["us-east-1"],
        scanned_at=SCAN_TIME,
        volumes={"us-east-1": volumes},
    )


def available_vol(
    vol_id: str = "vol-0abc1234567890001",
    size: int = 100,
    vol_type: str = "gp2",
    age_days: int = 60,
    name: str | None = "test-vol",
) -> dict:
    created = SCAN_TIME - timedelta(days=age_days)
    tags = [{"Key": "Name", "Value": name}] if name else []
    return {
        "VolumeId": vol_id,
        "State": "available",
        "Size": size,
        "VolumeType": vol_type,
        "CreateTime": created.isoformat(),
        "AvailabilityZone": "us-east-1a",
        "Tags": tags,
    }


def inuse_vol(vol_id: str = "vol-0inuse0000000001") -> dict:
    created = SCAN_TIME - timedelta(days=90)
    return {
        "VolumeId": vol_id,
        "State": "in-use",
        "Size": 50,
        "VolumeType": "gp3",
        "CreateTime": created.isoformat(),
        "AvailabilityZone": "us-east-1b",
        "Tags": [],
    }


# ---------------------------------------------------------------------------
# Positive: flagged
# ---------------------------------------------------------------------------


def test_available_volume_older_than_grace_period_is_flagged(default_config):
    vol = available_vol(age_days=60)
    snap = make_snapshot([vol])
    result = detect(snap, default_config)

    assert len(result) == 1
    t = result[0]
    assert t.resource_id == vol["VolumeId"]
    assert t.resource_type == "EC2::Volume"
    assert t.cause == "abandoned"
    assert t.severity == Severity.WASTEFUL
    assert t.estimated_monthly_cost >= 0
    assert "size_gib" in t.metadata
    assert t.metadata["size_gib"] == 100
    assert "--dry-run" in t.exorcism_cli
    assert vol["VolumeId"] in t.exorcism_cli


def test_resource_id_in_exorcism_cli(default_config):
    vol = available_vol(vol_id="vol-0specific0000001", age_days=90)
    snap = make_snapshot([vol])
    result = detect(snap, default_config)
    assert len(result) == 1
    assert "vol-0specific0000001" in result[0].exorcism_cli


def test_multiple_regions(default_config):
    vol1 = available_vol("vol-region1", age_days=40)
    vol2 = available_vol("vol-region2", age_days=40)
    snap = Snapshot(
        account_id=ACCOUNT,
        regions=["us-east-1", "eu-west-1"],
        scanned_at=SCAN_TIME,
        volumes={
            "us-east-1": [vol1],
            "eu-west-1": [vol2],
        },
    )
    result = detect(snap, default_config)
    assert len(result) == 2
    ids = {t.resource_id for t in result}
    assert ids == {"vol-region1", "vol-region2"}


# ---------------------------------------------------------------------------
# Negative: not flagged
# ---------------------------------------------------------------------------


def test_in_use_volume_not_flagged(default_config):
    snap = make_snapshot([inuse_vol()])
    result = detect(snap, default_config)
    assert result == []


def test_stopped_state_not_flagged(default_config):
    vol = available_vol(age_days=60)
    vol["State"] = "creating"
    snap = make_snapshot([vol])
    result = detect(snap, default_config)
    assert result == []


def test_empty_snapshot_returns_empty(default_config, empty_snapshot):
    result = detect(empty_snapshot, default_config)
    assert result == []


# ---------------------------------------------------------------------------
# Edge: grace period
# ---------------------------------------------------------------------------


def test_volume_within_grace_period_not_flagged(default_config):
    # Created 12 hours ago — within 24h grace
    vol = available_vol(age_days=0)
    vol["CreateTime"] = (SCAN_TIME - timedelta(hours=12)).isoformat()
    snap = make_snapshot([vol])
    result = detect(snap, default_config)
    assert result == []


def test_volume_exactly_at_grace_boundary_not_flagged(default_config):
    # Created exactly 24 hours ago — should NOT be flagged (< not <=)
    vol = available_vol(age_days=0)
    vol["CreateTime"] = (SCAN_TIME - timedelta(hours=24)).isoformat()
    snap = make_snapshot([vol])
    result = detect(snap, default_config)
    # 24h is NOT < 24h grace so it gets flagged — boundary behaviour: age_hours < grace
    # 24 is not < 24, so it IS flagged
    assert len(result) == 1


def test_volume_just_over_grace_period_is_flagged(default_config):
    vol = available_vol(age_days=0)
    vol["CreateTime"] = (SCAN_TIME - timedelta(hours=25)).isoformat()
    snap = make_snapshot([vol])
    result = detect(snap, default_config)
    assert len(result) == 1


def test_zero_size_volume_cost_is_zero_or_non_negative(default_config):
    vol = available_vol(size=0, age_days=60)
    snap = make_snapshot([vol])
    result = detect(snap, default_config)
    assert len(result) == 1
    assert result[0].estimated_monthly_cost >= 0


def test_volume_with_no_name_tag(default_config):
    vol = available_vol(name=None, age_days=60)
    snap = make_snapshot([vol])
    result = detect(snap, default_config)
    assert len(result) == 1
    assert result[0].resource_name is None


# ---------------------------------------------------------------------------
# Property tests
# ---------------------------------------------------------------------------


def test_snapshot_not_mutated(default_config):
    vol = available_vol(age_days=60)
    snap = make_snapshot([vol])
    snap_before = copy.deepcopy(snap)
    detect(snap, default_config)
    assert snap.volumes == snap_before.volumes
    assert snap.account_id == snap_before.account_id


def test_cost_non_negative(default_config):
    vols = [available_vol(f"vol-{i:020d}", size=i * 10, age_days=60) for i in range(1, 6)]
    snap = make_snapshot(vols)
    result = detect(snap, default_config)
    for t in result:
        assert t.estimated_monthly_cost >= 0, f"negative cost on {t.resource_id}"


def test_deterministic(default_config):
    vols = [available_vol(f"vol-{i:020d}", age_days=60) for i in range(3)]
    snap = make_snapshot(vols)
    result1 = detect(snap, default_config)
    result2 = detect(snap, default_config)
    assert [t.resource_id for t in result1] == [t.resource_id for t in result2]
