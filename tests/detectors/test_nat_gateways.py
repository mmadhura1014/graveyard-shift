"""Tests for scanner.detectors.nat_gateways"""

from __future__ import annotations

import copy
from datetime import UTC, datetime

from scanner.detectors.nat_gateways import detect
from scanner.models import Severity, Snapshot

SCAN_TIME = datetime(2025, 7, 1, 10, 0, 0, tzinfo=UTC)
ACCOUNT = "111122223333"
REGION = "us-east-1"
GW_ID = "nat-0dead00000000001"


def make_snapshot(gateways: list[dict], cw: dict | None = None) -> Snapshot:
    return Snapshot(
        account_id=ACCOUNT,
        regions=[REGION],
        scanned_at=SCAN_TIME,
        nat_gateways={REGION: gateways},
        cw_metrics={REGION: cw or {}},
    )


def gw(gw_id: str = GW_ID, state: str = "available", name: str | None = "staging-nat") -> dict:
    tags = [{"Key": "Name", "Value": name}] if name else []
    return {
        "NatGatewayId": gw_id,
        "State": state,
        "VpcId": "vpc-0dead000000000001",
        "SubnetId": "subnet-0dead000000000001",
        "CreateTime": "2025-01-01T00:00:00Z",
        "Tags": tags,
    }


# ── Positive ──────────────────────────────────────────────────────────────────


def test_nat_gw_below_threshold_is_flagged(default_config):
    snap = make_snapshot([gw()], cw={f"{GW_ID}:BytesOutToDestination": [{"Sum": 0}]})
    result = detect(snap, default_config)
    assert len(result) == 1
    t = result[0]
    assert t.resource_id == GW_ID
    assert t.cause == "idle"
    assert t.severity == Severity.WASTEFUL
    assert t.resource_type == "EC2::NatGateway"
    assert t.estimated_monthly_cost > 0
    assert GW_ID in t.exorcism_cli


def test_nat_gw_with_tiny_traffic_below_1mb_is_flagged(default_config):
    snap = make_snapshot([gw()], cw={f"{GW_ID}:BytesOutToDestination": [{"Sum": 500_000}]})
    result = detect(snap, default_config)
    assert len(result) == 1


# ── Negative ──────────────────────────────────────────────────────────────────


def test_nat_gw_above_threshold_not_flagged(default_config):
    snap = make_snapshot(
        [gw()],
        cw={f"{GW_ID}:BytesOutToDestination": [{"Sum": 5_368_709_120}]},
    )
    result = detect(snap, default_config)
    assert result == []


def test_empty_nat_gw_list_returns_empty(default_config, empty_snapshot):
    result = detect(empty_snapshot, default_config)
    assert result == []


# ── Edge: state exclusions ────────────────────────────────────────────────────


def test_deleting_state_excluded(default_config):
    snap = make_snapshot(
        [gw(state="deleting")],
        cw={f"{GW_ID}:BytesOutToDestination": [{"Sum": 0}]},
    )
    result = detect(snap, default_config)
    assert result == []


def test_deleted_state_excluded(default_config):
    snap = make_snapshot(
        [gw(state="deleted")],
        cw={f"{GW_ID}:BytesOutToDestination": [{"Sum": 0}]},
    )
    result = detect(snap, default_config)
    assert result == []


# ── Edge: CW unavailable ──────────────────────────────────────────────────────


def test_cw_unavailable_skips_gateway(default_config):
    """When CW data is absent the gateway is skipped (not flagged)."""
    snap = make_snapshot([gw()], cw={})  # no metric for this gw
    result = detect(snap, default_config)
    assert result == []


# ── Property tests ────────────────────────────────────────────────────────────


def test_snapshot_not_mutated(default_config):
    snap = make_snapshot([gw()], cw={f"{GW_ID}:BytesOutToDestination": [{"Sum": 0}]})
    before = copy.deepcopy(snap)
    detect(snap, default_config)
    assert snap.nat_gateways == before.nat_gateways


def test_deterministic(default_config):
    snap = make_snapshot([gw()], cw={f"{GW_ID}:BytesOutToDestination": [{"Sum": 0}]})
    r1 = detect(snap, default_config)
    r2 = detect(snap, default_config)
    assert [t.resource_id for t in r1] == [t.resource_id for t in r2]


def test_cost_non_negative(default_config):
    snap = make_snapshot([gw()], cw={f"{GW_ID}:BytesOutToDestination": [{"Sum": 0}]})
    for t in detect(snap, default_config):
        assert t.estimated_monthly_cost >= 0
