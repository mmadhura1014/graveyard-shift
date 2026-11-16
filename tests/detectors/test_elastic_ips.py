"""
Tests for scanner.detectors.elastic_ips
"""

from __future__ import annotations

import copy
from datetime import UTC, datetime

from scanner.detectors.elastic_ips import detect
from scanner.models import Severity, Snapshot

SCAN_TIME = datetime(2025, 7, 1, 10, 0, 0, tzinfo=UTC)
ACCOUNT = "111122223333"


def make_snapshot(addresses: list[dict]) -> Snapshot:
    return Snapshot(
        account_id=ACCOUNT,
        regions=["us-east-1"],
        scanned_at=SCAN_TIME,
        elastic_ips={"us-east-1": addresses},
    )


def unassociated_eip(
    alloc_id: str = "eipalloc-0dead0000000001",
    public_ip: str = "203.0.113.10",
    name: str | None = "idle-eip",
) -> dict:
    tags = [{"Key": "Name", "Value": name}] if name else []
    return {
        "AllocationId": alloc_id,
        "PublicIp": public_ip,
        "Tags": tags,
    }


def associated_eip(
    alloc_id: str = "eipalloc-0live0000000001",
    public_ip: str = "203.0.113.20",
) -> dict:
    return {
        "AllocationId": alloc_id,
        "PublicIp": public_ip,
        "AssociationId": "eipassoc-0live0000000001",
        "Tags": [],
    }


# ---------------------------------------------------------------------------
# Positive
# ---------------------------------------------------------------------------


def test_unassociated_eip_is_flagged(default_config):
    result = detect(make_snapshot([unassociated_eip()]), default_config)
    assert len(result) == 1
    t = result[0]
    assert t.resource_id == "eipalloc-0dead0000000001"
    assert t.resource_type == "EC2::EIP"
    assert t.cause == "idle, costs money"
    assert t.severity == Severity.WASTEFUL
    assert t.estimated_monthly_cost > 0
    assert t.metadata["public_ip"] == "203.0.113.10"
    assert "--dry-run" in t.exorcism_cli
    assert "eipalloc-0dead0000000001" in t.exorcism_cli


def test_eip_without_name_tag(default_config):
    eip = unassociated_eip(name=None)
    result = detect(make_snapshot([eip]), default_config)
    assert len(result) == 1
    assert result[0].resource_name is None


# ---------------------------------------------------------------------------
# Negative
# ---------------------------------------------------------------------------


def test_associated_eip_not_flagged(default_config):
    result = detect(make_snapshot([associated_eip()]), default_config)
    assert result == []


def test_eip_with_empty_association_id_is_flagged(default_config):
    """An explicitly empty AssociationId should still be treated as unassociated."""
    eip = {
        "AllocationId": "eipalloc-0empty000000001",
        "PublicIp": "203.0.113.30",
        "AssociationId": "",
        "Tags": [],
    }
    result = detect(make_snapshot([eip]), default_config)
    # Empty string is falsy — should be flagged
    assert len(result) == 1


def test_empty_eip_list_returns_empty(default_config, empty_snapshot):
    result = detect(empty_snapshot, default_config)
    assert result == []


# ---------------------------------------------------------------------------
# Property tests
# ---------------------------------------------------------------------------


def test_snapshot_not_mutated(default_config):
    snap = make_snapshot([unassociated_eip()])
    before = copy.deepcopy(snap)
    detect(snap, default_config)
    assert snap.elastic_ips == before.elastic_ips


def test_cost_non_negative(default_config):
    eips = [unassociated_eip(f"eipalloc-{i:020d}") for i in range(3)]
    result = detect(make_snapshot(eips), default_config)
    for t in result:
        assert t.estimated_monthly_cost >= 0


def test_deterministic(default_config):
    eips = [unassociated_eip(f"eipalloc-{i:020d}") for i in range(3)]
    snap = make_snapshot(eips)
    r1 = detect(snap, default_config)
    r2 = detect(snap, default_config)
    assert [t.resource_id for t in r1] == [t.resource_id for t in r2]
