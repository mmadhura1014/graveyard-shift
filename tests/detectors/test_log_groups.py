"""Tests for scanner.detectors.log_groups"""

from __future__ import annotations

import copy
from datetime import UTC, datetime

from scanner.detectors.log_groups import detect
from scanner.models import Severity, Snapshot

SCAN_TIME = datetime(2025, 7, 1, 10, 0, 0, tzinfo=UTC)
ACCOUNT = "111122223333"
REGION = "us-east-1"
LG_NAME = "/aws/lambda/forgotten-function"


def make_snapshot(groups: list[dict], cw: dict | None = None) -> Snapshot:
    return Snapshot(
        account_id=ACCOUNT,
        regions=[REGION],
        scanned_at=SCAN_TIME,
        log_groups={REGION: groups},
        cw_metrics={REGION: cw or {}},
    )


def hoarder_lg(name: str = LG_NAME, stored_bytes: int = 52_428_800) -> dict:
    return {
        "logGroupName": name,
        "storedBytes": stored_bytes,
        "metricFilterCount": 0,
        "retentionInDays": None,
    }


def active_lg(name: str = "/app/active/app") -> dict:
    return {
        "logGroupName": name,
        "storedBytes": 209_715_200,
        "metricFilterCount": 2,
        "retentionInDays": 30,
    }


# ── Positive ──────────────────────────────────────────────────────────────────


def test_no_retention_no_filters_zero_events_is_flagged(default_config):
    cw = {f"{LG_NAME}:IncomingLogEvents": [{"Sum": 0}]}
    result = detect(make_snapshot([hoarder_lg()], cw), default_config)
    assert len(result) == 1
    t = result[0]
    assert t.resource_id == LG_NAME
    assert t.cause == "hoarder"
    assert t.severity == Severity.WASTEFUL
    assert t.resource_type == "CWLogs::LogGroup"
    assert LG_NAME in t.exorcism_cli
    assert t.metadata["stored_bytes"] == 52_428_800


def test_zero_stored_bytes_no_cw_data_is_flagged(default_config):
    """storedBytes=0 and no CW data → flag."""
    lg = hoarder_lg(stored_bytes=0)
    result = detect(make_snapshot([lg], {}), default_config)
    assert len(result) == 1


def test_cost_proportional_to_stored_bytes(default_config):
    large = hoarder_lg(stored_bytes=1_073_741_824)  # 1 GB
    cw = {f"{LG_NAME}:IncomingLogEvents": [{"Sum": 0}]}
    result = detect(make_snapshot([large], cw), default_config)
    assert len(result) == 1
    assert result[0].estimated_monthly_cost > 0


# ── Negative ──────────────────────────────────────────────────────────────────


def test_has_retention_policy_not_flagged(default_config):
    lg = hoarder_lg()
    lg["retentionInDays"] = 30
    cw = {f"{LG_NAME}:IncomingLogEvents": [{"Sum": 0}]}
    result = detect(make_snapshot([lg], cw), default_config)
    assert result == []


def test_has_metric_filters_not_flagged(default_config):
    lg = hoarder_lg()
    lg["metricFilterCount"] = 1
    cw = {f"{LG_NAME}:IncomingLogEvents": [{"Sum": 0}]}
    result = detect(make_snapshot([lg], cw), default_config)
    assert result == []


def test_has_recent_ingestion_not_flagged(default_config):
    cw = {f"{LG_NAME}:IncomingLogEvents": [{"Sum": 450_000}]}
    result = detect(make_snapshot([hoarder_lg()], cw), default_config)
    assert result == []


def test_empty_log_groups_returns_empty(default_config, empty_snapshot):
    result = detect(empty_snapshot, default_config)
    assert result == []


# ── Edge ──────────────────────────────────────────────────────────────────────


def test_non_zero_stored_bytes_no_cw_data_is_skipped(default_config):
    """storedBytes > 0 but no CW metric → conservative skip."""
    lg = hoarder_lg(stored_bytes=10_000_000)
    result = detect(make_snapshot([lg], {}), default_config)
    assert result == []


# ── Property tests ────────────────────────────────────────────────────────────


def test_snapshot_not_mutated(default_config):
    cw = {f"{LG_NAME}:IncomingLogEvents": [{"Sum": 0}]}
    snap = make_snapshot([hoarder_lg()], cw)
    before = copy.deepcopy(snap)
    detect(snap, default_config)
    assert snap.log_groups == before.log_groups


def test_deterministic(default_config):
    groups = [hoarder_lg(f"/app/group{i}") for i in range(3)]
    cw = {f"/app/group{i}:IncomingLogEvents": [{"Sum": 0}] for i in range(3)}
    snap = make_snapshot(groups, cw)
    r1 = detect(snap, default_config)
    r2 = detect(snap, default_config)
    assert [t.resource_id for t in r1] == [t.resource_id for t in r2]


def test_cost_non_negative(default_config):
    groups = [hoarder_lg(f"/app/group{i}") for i in range(3)]
    cw = {f"/app/group{i}:IncomingLogEvents": [{"Sum": 0}] for i in range(3)}
    for t in detect(make_snapshot(groups, cw), default_config):
        assert t.estimated_monthly_cost >= 0
