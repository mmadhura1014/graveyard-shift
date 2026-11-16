"""
Tests for scanner.fetcher — uses unittest.mock to avoid real AWS calls.
"""

from __future__ import annotations

from unittest.mock import MagicMock

from scanner.config import DEFAULT_CONFIG
from scanner.fetcher import fetch


def _mock_session(account_id: str = "111122223333"):
    session = MagicMock()

    # STS
    sts = MagicMock()
    sts.get_caller_identity.return_value = {"Account": account_id}
    session.client.side_effect = lambda svc, **kw: {
        "sts": sts,
        "iam": _mock_iam(),
        "ec2": _mock_ec2(),
        "elbv2": _mock_elbv2(),
        "cloudwatch": _mock_cw(),
        "logs": _mock_logs(),
    }.get(svc, MagicMock())

    return session


def _mock_ec2():
    ec2 = MagicMock()
    ec2.get_paginator.return_value = _make_paginator([])
    ec2.describe_regions.return_value = {"Regions": [{"RegionName": "us-east-1"}]}
    return ec2


def _mock_elbv2():
    elb = MagicMock()
    elb.get_paginator.return_value = _make_paginator([])
    return elb


def _mock_cw():
    cw = MagicMock()
    cw.get_metric_statistics.return_value = {"Datapoints": []}
    return cw


def _mock_logs():
    lg = MagicMock()
    lg.get_paginator.return_value = _make_paginator([])
    return lg


def _mock_iam():
    iam = MagicMock()
    iam.get_paginator.return_value = _make_paginator([])
    return iam


def _make_paginator(items: list):
    paginator = MagicMock()
    page = MagicMock()
    page.get.return_value = items
    paginator.paginate.return_value = [page]
    return paginator


# ── Tests ─────────────────────────────────────────────────────────────────────


def test_fetch_returns_snapshot_and_zero_skips():
    session = _mock_session()
    snap, skipped = fetch(session=session, regions=["us-east-1"], config=DEFAULT_CONFIG)
    assert snap.account_id == "111122223333"
    assert skipped == 0
    assert "us-east-1" in snap.regions


def test_fetch_multi_region():
    session = _mock_session()
    snap, skipped = fetch(
        session=session, regions=["us-east-1", "eu-west-1"], config=DEFAULT_CONFIG
    )
    assert skipped == 0
    assert set(snap.regions) == {"us-east-1", "eu-west-1"}


def test_fetch_region_auth_failure_counted_as_skip():
    from botocore.exceptions import ClientError

    session = MagicMock()

    sts = MagicMock()
    sts.get_caller_identity.return_value = {"Account": "111122223333"}

    eu_ec2 = MagicMock()
    err = ClientError({"Error": {"Code": "AuthFailure", "Message": "auth"}}, "DescribeVolumes")
    eu_ec2.get_paginator.side_effect = err

    def client_side_effect(svc, **kw):
        region = kw.get("region_name", "")
        if svc == "sts":
            return sts
        if svc == "iam":
            return _mock_iam()
        if svc == "ec2" and region == "eu-west-1":
            return eu_ec2
        if svc == "ec2":
            return _mock_ec2()
        if svc == "elbv2":
            return _mock_elbv2()
        if svc == "cloudwatch":
            return _mock_cw()
        if svc == "logs":
            return _mock_logs()
        return MagicMock()

    session.client.side_effect = client_side_effect

    snap, skipped = fetch(
        session=session, regions=["us-east-1", "eu-west-1"], config=DEFAULT_CONFIG
    )
    assert skipped == 1
