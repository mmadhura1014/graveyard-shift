"""Tests for scanner.detectors.iam_keys"""

from __future__ import annotations

import copy
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from scanner.detectors.iam_keys import detect
from scanner.models import Severity, Snapshot

SCAN_TIME = datetime(2025, 7, 1, 10, 0, 0, tzinfo=UTC)
ACCOUNT = "111122223333"


def make_snapshot(keys: list[dict]) -> Snapshot:
    return Snapshot(
        account_id=ACCOUNT,
        regions=["us-east-1"],
        scanned_at=SCAN_TIME,
        iam_access_keys=keys,
    )


def key(
    key_id: str = "AKIAIOSFODNN7EXAMPLE",
    username: str = "alice",
    status: str = "Active",
    last_used_days_ago: int | None = 100,
    created_days_ago: int = 200,
) -> dict:
    last_used = (
        (SCAN_TIME - timedelta(days=last_used_days_ago)).isoformat()
        if last_used_days_ago is not None
        else None
    )
    return {
        "AccessKeyId": key_id,
        "UserName": username,
        "Status": status,
        "CreateDate": (SCAN_TIME - timedelta(days=created_days_ago)).isoformat(),
        "LastUsedDate": last_used,
    }


# ── Positive ──────────────────────────────────────────────────────────────────


def test_active_key_last_used_100_days_ago_is_flagged(default_config):
    result = detect(make_snapshot([key(last_used_days_ago=100)]), default_config)
    assert len(result) == 1
    t = result[0]
    assert t.resource_type == "IAM::AccessKey"
    assert t.cause == "undead credentials"
    assert t.severity == Severity.RISKY
    assert t.region == "global"
    assert t.metadata["username"] == "alice"
    assert "AKIAIOSFODNN7EXAMPLE" in t.exorcism_cli
    assert "alice" in t.exorcism_cli


def test_key_never_used_created_100_days_ago_is_flagged(default_config):
    k = key(last_used_days_ago=None, created_days_ago=100)
    result = detect(make_snapshot([k]), default_config)
    assert len(result) == 1
    assert result[0].severity == Severity.RISKY


def test_inactive_stale_key_has_wasteful_severity(default_config):
    k = key(status="Inactive", last_used_days_ago=200)
    result = detect(make_snapshot([k]), default_config)
    assert len(result) == 1
    assert result[0].severity == Severity.WASTEFUL


# ── Negative ──────────────────────────────────────────────────────────────────


def test_active_key_used_10_days_ago_not_flagged(default_config):
    result = detect(make_snapshot([key(last_used_days_ago=10)]), default_config)
    assert result == []


def test_key_created_10_days_ago_never_used_not_flagged(default_config):
    k = key(last_used_days_ago=None, created_days_ago=10)
    result = detect(make_snapshot([k]), default_config)
    assert result == []


def test_empty_key_list_returns_empty(default_config, empty_snapshot):
    result = detect(empty_snapshot, default_config)
    assert result == []


# ── IAM key cost is always zero ───────────────────────────────────────────────


def test_iam_key_cost_is_zero(default_config):
    result = detect(make_snapshot([key(last_used_days_ago=100)]), default_config)
    assert len(result) == 1
    assert result[0].estimated_monthly_cost == Decimal("0")


# ── Undead credentials count ──────────────────────────────────────────────────


def test_multiple_stale_keys_all_flagged(default_config):
    keys = [
        key("AKIAIOSFODNN7EXAMPLE1", "alice", last_used_days_ago=100),
        key("AKIAIOSFODNN7EXAMPLE2", "bob", last_used_days_ago=200),
        key("AKIAIOSFODNN7EXAMPLE3", "carol", last_used_days_ago=10),  # not flagged
    ]
    result = detect(make_snapshot(keys), default_config)
    assert len(result) == 2


# ── Property tests ────────────────────────────────────────────────────────────


def test_snapshot_not_mutated(default_config):
    keys = [key()]
    snap = make_snapshot(keys)
    before = copy.deepcopy(snap)
    detect(snap, default_config)
    assert snap.iam_access_keys == before.iam_access_keys


def test_deterministic(default_config):
    keys = [key(f"AKIAIOSFODNN7EXAMP{i:02d}", f"user{i}", last_used_days_ago=100) for i in range(3)]
    snap = make_snapshot(keys)
    r1 = detect(snap, default_config)
    r2 = detect(snap, default_config)
    assert [t.resource_id for t in r1] == [t.resource_id for t in r2]


def test_cost_non_negative(default_config):
    keys = [key(f"AKIAIOSFODNN7EXAMP{i:02d}", last_used_days_ago=100) for i in range(3)]
    for t in detect(make_snapshot(keys), default_config):
        assert t.estimated_monthly_cost >= 0
