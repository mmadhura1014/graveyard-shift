"""Tests for scanner.detectors.load_balancers"""

from __future__ import annotations

import copy
from datetime import UTC, datetime

from scanner.detectors.load_balancers import detect
from scanner.models import Severity, Snapshot

SCAN_TIME = datetime(2025, 7, 1, 10, 0, 0, tzinfo=UTC)
ACCOUNT = "111122223333"
REGION = "us-east-1"

ALB_ARN = "arn:aws:elasticloadbalancing:us-east-1:111122223333:loadbalancer/app/ghost-alb/0001"
TG_ARN = "arn:aws:elasticloadbalancing:us-east-1:111122223333:targetgroup/ghost-tg/0001"


def make_snapshot(
    lbs: list[dict],
    tgs: list[dict] | None = None,
    health: dict | None = None,
    cw: dict | None = None,
) -> Snapshot:
    return Snapshot(
        account_id=ACCOUNT,
        regions=[REGION],
        scanned_at=SCAN_TIME,
        load_balancers={REGION: lbs},
        target_groups={REGION: tgs or []},
        target_health={REGION: health or {}},
        cw_metrics={REGION: cw or {}},
    )


def alb(name: str = "ghost-alb", arn: str = ALB_ARN) -> dict:
    return {
        "LoadBalancerArn": arn,
        "LoadBalancerName": name,
        "Type": "application",
        "DNSName": f"{name}.us-east-1.elb.amazonaws.com",
        "State": {"Code": "active"},
        "CreatedTime": "2025-01-01T00:00:00Z",
    }


def tg(arn: str = TG_ARN, lb_arn: str = ALB_ARN) -> dict:
    return {"TargetGroupArn": arn, "LoadBalancerArns": [lb_arn], "TargetGroupName": "tg"}


# ── Positive ──────────────────────────────────────────────────────────────────


def test_alb_with_no_target_groups_is_flagged(default_config):
    snap = make_snapshot([alb()], tgs=[], health={})
    result = detect(snap, default_config)
    assert len(result) == 1
    t = result[0]
    assert t.resource_id == ALB_ARN
    assert t.cause == "lonely"
    assert t.severity == Severity.WASTEFUL
    assert t.resource_type == "ELB::LoadBalancer"
    assert t.metadata["lb_type"] == "ALB"
    assert t.estimated_monthly_cost >= 0


def test_alb_with_empty_target_group_is_flagged(default_config):
    snap = make_snapshot(
        [alb()],
        tgs=[tg()],
        health={TG_ARN: []},  # target group has no registered targets
        cw={},
    )
    result = detect(snap, default_config)
    assert len(result) == 1


def test_alb_with_targets_and_zero_traffic_is_flagged(default_config):
    snap = make_snapshot(
        [alb()],
        tgs=[tg()],
        health={TG_ARN: [{"Target": {"Id": "i-001"}, "TargetHealth": {"State": "healthy"}}]},
        cw={"ghost-alb:RequestCount": [{"Sum": 0}]},
    )
    result = detect(snap, default_config)
    assert len(result) == 1
    assert result[0].metadata["reason"] == "zero traffic over 14 days"


def test_nlb_with_no_targets_is_flagged(default_config):
    nlb_arn = "arn:aws:elasticloadbalancing:us-east-1:111122223333:loadbalancer/net/ghost-nlb/0002"
    nlb = {
        "LoadBalancerArn": nlb_arn,
        "LoadBalancerName": "ghost-nlb",
        "Type": "network",
        "DNSName": "ghost-nlb.elb.amazonaws.com",
        "State": {"Code": "active"},
        "CreatedTime": "2025-01-01T00:00:00Z",
    }
    snap = make_snapshot([nlb], tgs=[], health={})
    result = detect(snap, default_config)
    assert len(result) == 1
    assert result[0].metadata["lb_type"] == "NLB"


# ── Negative ──────────────────────────────────────────────────────────────────


def test_alb_with_healthy_targets_and_traffic_not_flagged(default_config):
    snap = make_snapshot(
        [alb()],
        tgs=[tg()],
        health={TG_ARN: [{"Target": {"Id": "i-001"}, "TargetHealth": {"State": "healthy"}}]},
        cw={"ghost-alb:RequestCount": [{"Sum": 500000}]},
    )
    result = detect(snap, default_config)
    assert result == []


def test_empty_lb_list_returns_empty(default_config, empty_snapshot):
    result = detect(empty_snapshot, default_config)
    assert result == []


# ── Edge: CW unavailable ──────────────────────────────────────────────────────


def test_cw_unavailable_falls_back_to_target_check_has_targets_not_flagged(default_config):
    """LB has targets but CW metric is absent → assume active, skip."""
    snap = make_snapshot(
        [alb()],
        tgs=[tg()],
        health={TG_ARN: [{"Target": {"Id": "i-001"}, "TargetHealth": {"State": "healthy"}}]},
        cw={},  # no CW data at all
    )
    result = detect(snap, default_config)
    assert result == []


def test_cw_unavailable_no_targets_still_flagged(default_config):
    """LB has no targets regardless of CW → flagged."""
    snap = make_snapshot([alb()], tgs=[tg()], health={TG_ARN: []}, cw={})
    result = detect(snap, default_config)
    assert len(result) == 1


# ── Property tests ────────────────────────────────────────────────────────────


def test_snapshot_not_mutated(default_config):
    snap = make_snapshot([alb()], tgs=[], health={})
    before = copy.deepcopy(snap)
    detect(snap, default_config)
    assert snap.load_balancers == before.load_balancers


def test_deterministic(default_config):
    snap = make_snapshot([alb()], tgs=[], health={})
    r1 = detect(snap, default_config)
    r2 = detect(snap, default_config)
    assert [t.resource_id for t in r1] == [t.resource_id for t in r2]


def test_cost_non_negative(default_config):
    snap = make_snapshot([alb()], tgs=[], health={})
    for t in detect(snap, default_config):
        assert t.estimated_monthly_cost >= 0
