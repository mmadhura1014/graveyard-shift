"""
Tests for scanner.detectors.ebs_snapshots
"""

from __future__ import annotations

import copy
from datetime import UTC, datetime

from scanner.detectors.ebs_snapshots import detect
from scanner.models import Severity, Snapshot

SCAN_TIME = datetime(2025, 7, 1, 10, 0, 0, tzinfo=UTC)
ACCOUNT = "111122223333"


def make_snapshot(
    snaps: list[dict],
    volumes: list[dict] | None = None,
) -> Snapshot:
    return Snapshot(
        account_id=ACCOUNT,
        regions=["us-east-1"],
        scanned_at=SCAN_TIME,
        snapshots_data={"us-east-1": snaps},
        volumes={"us-east-1": volumes or []},
    )


def snap(
    snap_id: str = "snap-0dead00000000001",
    volume_id: str = "vol-0gone000000000001",
    owner: str = ACCOUNT,
    size: int = 50,
    name: str | None = "test-snap",
) -> dict:
    tags = [{"Key": "Name", "Value": name}] if name else []
    return {
        "SnapshotId": snap_id,
        "VolumeId": volume_id,
        "OwnerId": owner,
        "VolumeSize": size,
        "StartTime": "2025-01-01T00:00:00Z",
        "Tags": tags,
    }


def volume(vol_id: str = "vol-0live000000000001") -> dict:
    return {
        "VolumeId": vol_id,
        "State": "in-use",
        "Size": 50,
        "VolumeType": "gp2",
        "CreateTime": "2025-01-01T00:00:00Z",
        "AvailabilityZone": "us-east-1a",
        "Tags": [],
    }


# ---------------------------------------------------------------------------
# Positive
# ---------------------------------------------------------------------------


def test_snapshot_with_missing_volume_is_flagged(default_config):
    s = snap(volume_id="vol-0gone000000000001")
    result = detect(make_snapshot([s], volumes=[]), default_config)
    assert len(result) == 1
    t = result[0]
    assert t.resource_id == "snap-0dead00000000001"
    assert t.cause == "orphaned"
    assert t.severity == Severity.WASTEFUL
    assert t.resource_type == "EC2::Snapshot"
    assert "--dry-run" in t.exorcism_cli
    assert "snap-0dead00000000001" in t.exorcism_cli


def test_snapshot_cost_non_negative(default_config):
    s = snap(size=200)
    result = detect(make_snapshot([s], volumes=[]), default_config)
    assert len(result) == 1
    assert result[0].estimated_monthly_cost >= 0


# ---------------------------------------------------------------------------
# Negative
# ---------------------------------------------------------------------------


def test_snapshot_whose_volume_exists_not_flagged(default_config):
    vol = volume("vol-0live000000000001")
    s = snap(volume_id="vol-0live000000000001")
    result = detect(make_snapshot([s], volumes=[vol]), default_config)
    assert result == []


def test_snapshot_whose_volume_exists_but_unattached_not_flagged(default_config):
    """An unattached (available) volume still counts as 'existing'."""
    vol = volume("vol-0avail00000000001")
    vol["State"] = "available"
    s = snap(volume_id="vol-0avail00000000001")
    result = detect(make_snapshot([s], volumes=[vol]), default_config)
    assert result == []


def test_aws_owned_snapshot_excluded(default_config):
    s = snap(owner="amazon", volume_id="vol-0gone000000000001")
    result = detect(make_snapshot([s], volumes=[]), default_config)
    assert result == []


def test_aws_marketplace_snapshot_excluded(default_config):
    s = snap(owner="aws-marketplace", volume_id="vol-0gone000000000001")
    result = detect(make_snapshot([s], volumes=[]), default_config)
    assert result == []


# ---------------------------------------------------------------------------
# Edge
# ---------------------------------------------------------------------------


def test_empty_snapshot_list_returns_empty(default_config, empty_snapshot):
    result = detect(empty_snapshot, default_config)
    assert result == []


def test_empty_volume_list_non_aws_snapshot_is_flagged(default_config):
    """When volumes list is empty, any non-AWS snapshot should be flagged."""
    s = snap(volume_id="vol-0gone000000000001", owner=ACCOUNT)
    result = detect(make_snapshot([s], volumes=[]), default_config)
    assert len(result) == 1


# ---------------------------------------------------------------------------
# Property tests
# ---------------------------------------------------------------------------


def test_snapshot_not_mutated(default_config):
    s = snap()
    snap_obj = make_snapshot([s], volumes=[])
    before = copy.deepcopy(snap_obj)
    detect(snap_obj, default_config)
    assert snap_obj.snapshots_data == before.snapshots_data


def test_deterministic(default_config):
    snaps = [snap(f"snap-{i:020d}", volume_id=f"vol-gone-{i}") for i in range(3)]
    snap_obj = make_snapshot(snaps, volumes=[])
    r1 = detect(snap_obj, default_config)
    r2 = detect(snap_obj, default_config)
    assert [t.resource_id for t in r1] == [t.resource_id for t in r2]
