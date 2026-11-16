"""
Graveyard Shift — AWS data fetcher.

Fetches raw boto3 API responses across regions in parallel and assembles
them into a Snapshot.  Uses only read-only APIs.

Returns (snapshot, skipped_region_count).  Callers should exit with code 2
if skipped_region_count > 0.
"""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime
from typing import Any

import boto3
from botocore.exceptions import ClientError

from scanner.models import Snapshot

log = logging.getLogger(__name__)

_SKIP_CODES = {"AuthFailure", "UnauthorizedOperation", "AccessDenied"}


def fetch(
    session: boto3.Session,
    regions: list[str] | None,
    config: dict[str, Any],
) -> tuple[Snapshot, int]:
    """
    Fetch AWS data for all requested regions in parallel.
    Returns (Snapshot, number_of_skipped_regions).
    Never logs credential values or full ARNs at INFO level.
    """
    # Resolve regions
    if regions is None:
        regions = _list_regions(session)

    account_id = _get_account_id(session)
    now = datetime.now(tz=UTC)

    snapshot = Snapshot(
        account_id=account_id,
        regions=regions,
        scanned_at=now,
    )
    skipped = 0

    # IAM is global — fetch once
    try:
        _fetch_iam(session, snapshot)
    except ClientError as e:
        if e.response["Error"]["Code"] in _SKIP_CODES:
            log.warning("IAM fetch skipped (permission denied): %s", e.response["Error"]["Code"])
        else:
            raise

    # Per-region fetch in parallel
    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = {
            pool.submit(_fetch_region, session, region, snapshot, config): region
            for region in regions
        }
        for future in as_completed(futures):
            region = futures[future]
            exc = future.exception()
            if exc is not None:
                if isinstance(exc, ClientError) and exc.response["Error"]["Code"] in _SKIP_CODES:
                    log.warning("Region %s skipped: %s", region, exc.response["Error"]["Code"])
                    skipped += 1
                else:
                    log.error("Region %s failed: %s", region, exc)
                    skipped += 1

    return snapshot, skipped


def _fetch_region(
    session: boto3.Session,
    region: str,
    snapshot: Snapshot,
    config: dict[str, Any],
) -> None:
    """Fetch all required data for one region and populate the snapshot."""
    ec2 = session.client("ec2", region_name=region)
    elbv2 = session.client("elbv2", region_name=region)
    cw = session.client("cloudwatch", region_name=region)
    logs = session.client("logs", region_name=region)

    log.info("Fetching region %s", region)

    snapshot.volumes[region] = _paginate(
        ec2,
        "describe_volumes",
        "Volumes",
        Filters=[{"Name": "status", "Values": ["available", "in-use"]}],
    )
    snapshot.snapshots_data[region] = _paginate(
        ec2, "describe_snapshots", "Snapshots", OwnerIds=["self"]
    )
    snapshot.elastic_ips[region] = _paginate(ec2, "describe_addresses", "Addresses")
    snapshot.nat_gateways[region] = _paginate(ec2, "describe_nat_gateways", "NatGateways")
    snapshot.instances[region] = _paginate(ec2, "describe_instances", "Reservations")
    snapshot.security_groups[region] = _paginate(ec2, "describe_security_groups", "SecurityGroups")
    snapshot.enis[region] = _paginate(ec2, "describe_network_interfaces", "NetworkInterfaces")

    lbs = _paginate(elbv2, "describe_load_balancers", "LoadBalancers")
    snapshot.load_balancers[region] = lbs

    tgs = _paginate(elbv2, "describe_target_groups", "TargetGroups")
    snapshot.target_groups[region] = tgs

    health: dict[str, list[dict]] = {}
    for tg in tgs:
        tg_arn = tg["TargetGroupArn"]
        try:
            resp = elbv2.describe_target_health(TargetGroupArn=tg_arn)
            health[tg_arn] = resp.get("TargetHealthDescriptions", [])
        except ClientError as e:
            log.warning(
                "Cannot fetch target health for %s: %s", tg_arn, e.response["Error"]["Code"]
            )
            health[tg_arn] = []
    snapshot.target_health[region] = health

    snapshot.log_groups[region] = _paginate(logs, "describe_log_groups", "logGroups")

    # CloudWatch metrics
    snapshot.cw_metrics[region] = _fetch_cw_metrics(
        cw, lbs, snapshot.nat_gateways[region], snapshot.log_groups[region], config
    )


def _fetch_cw_metrics(
    cw_client,
    lbs: list[dict],
    nat_gws: list[dict],
    log_groups: list[dict],
    config: dict[str, Any],
) -> dict[str, list[dict]]:
    """Fetch CloudWatch metrics for LBs, NAT GWs, and log groups."""
    import datetime as dt
    from datetime import timedelta

    metrics: dict[str, list[dict]] = {}
    lb_days = config.get("lb_no_traffic_days", 14)
    nat_days = config.get("nat_no_traffic_days", 14)
    log_days = config.get("log_group_quiet_days", 30)
    now = dt.datetime.now(tz=dt.UTC)

    # ALB/NLB request count
    for lb in lbs:
        lb_name = lb["LoadBalancerName"]
        lb_type = lb.get("Type", "application").lower()
        metric_name = "RequestCount" if lb_type == "application" else "ActiveFlowCount"
        namespace = "AWS/ApplicationELB" if lb_type == "application" else "AWS/NetworkELB"

        # Dimension value is the short lb_id from the ARN
        arn = lb["LoadBalancerArn"]
        # e.g. arn:aws:elasticloadbalancing:...:loadbalancer/app/name/id → app/name/id
        lb_dim = "/".join(arn.split(":")[-1].split("/")[1:])

        key = f"{lb_name}:{metric_name}"
        try:
            resp = cw_client.get_metric_statistics(
                Namespace=namespace,
                MetricName=metric_name,
                Dimensions=[{"Name": "LoadBalancer", "Value": lb_dim}],
                StartTime=now - timedelta(days=lb_days),
                EndTime=now,
                Period=lb_days * 86400,
                Statistics=["Sum"],
            )
            metrics[key] = resp.get("Datapoints", [])
        except ClientError as e:
            log.warning("CW fetch failed for LB %s: %s", lb_name, e.response["Error"]["Code"])

    # NAT Gateway bytes
    for gw in nat_gws:
        gw_id = gw["NatGatewayId"]
        key = f"{gw_id}:BytesOutToDestination"
        try:
            resp = cw_client.get_metric_statistics(
                Namespace="AWS/NATGateway",
                MetricName="BytesOutToDestination",
                Dimensions=[{"Name": "NatGatewayId", "Value": gw_id}],
                StartTime=now - timedelta(days=nat_days),
                EndTime=now,
                Period=nat_days * 86400,
                Statistics=["Sum"],
            )
            metrics[key] = resp.get("Datapoints", [])
        except ClientError as e:
            log.warning("CW fetch failed for NAT GW %s: %s", gw_id, e.response["Error"]["Code"])

    # Log group ingestion
    for lg in log_groups:
        lg_name = lg["logGroupName"]
        if lg.get("retentionInDays") is not None or lg.get("metricFilterCount", 0) > 0:
            continue  # Won't be flagged anyway — skip CW call
        key = f"{lg_name}:IncomingLogEvents"
        try:
            resp = cw_client.get_metric_statistics(
                Namespace="AWS/Logs",
                MetricName="IncomingLogEvents",
                Dimensions=[{"Name": "LogGroupName", "Value": lg_name}],
                StartTime=now - timedelta(days=log_days),
                EndTime=now,
                Period=log_days * 86400,
                Statistics=["Sum"],
            )
            metrics[key] = resp.get("Datapoints", [])
        except ClientError as e:
            log.warning(
                "CW fetch failed for log group %s: %s", lg_name, e.response["Error"]["Code"]
            )

    return metrics


def _fetch_iam(session: boto3.Session, snapshot: Snapshot) -> None:
    """Fetch IAM users and access key last-used data (global service)."""
    iam = session.client("iam")
    users = _paginate(iam, "list_users", "Users")
    snapshot.iam_users = users

    keys: list[dict] = []
    for user in users:
        username = user["UserName"]
        user_keys = _paginate(iam, "list_access_keys", "AccessKeyMetadata", UserName=username)
        for k in user_keys:
            key_id = k["AccessKeyId"]
            try:
                lu_resp = iam.get_access_key_last_used(AccessKeyId=key_id)
                last_used_info = lu_resp.get("AccessKeyLastUsed", {})
                k["LastUsedDate"] = last_used_info.get("LastUsedDate")
                k["LastUsedRegion"] = last_used_info.get("Region", "N/A")
                k["LastUsedService"] = last_used_info.get("ServiceName", "N/A")
            except ClientError as e:
                log.warning(
                    "Cannot get last-used for key (user %s): %s",
                    username,
                    e.response["Error"]["Code"],
                )
                k["LastUsedDate"] = None
            keys.append(k)
    snapshot.iam_access_keys = keys


def _list_regions(session: boto3.Session) -> list[str]:
    ec2 = session.client("ec2", region_name="us-east-1")
    resp = ec2.describe_regions(
        Filters=[{"Name": "opt-in-status", "Values": ["opt-in-not-required", "opted-in"]}]
    )
    return [r["RegionName"] for r in resp["Regions"]]


def _get_account_id(session: boto3.Session) -> str:
    sts = session.client("sts")
    return sts.get_caller_identity()["Account"]


def _paginate(client, method: str, key: str, **kwargs) -> list[dict]:
    """Paginate through all pages of a boto3 list/describe call.

    ClientError is always propagated so callers can handle auth failures.
    Non-auth errors from the paginator itself (e.g. method not pageable)
    fall through to a direct single-page call.
    """
    from botocore.exceptions import ClientError

    paginator_methods = {
        "describe_volumes",
        "describe_snapshots",
        "describe_addresses",
        "describe_nat_gateways",
        "describe_instances",
        "describe_security_groups",
        "describe_network_interfaces",
        "describe_load_balancers",
        "describe_target_groups",
        "describe_log_groups",
        "list_users",
        "list_access_keys",
    }
    if method in paginator_methods:
        try:
            paginator = client.get_paginator(method)
            results = []
            for page in paginator.paginate(**kwargs):
                results.extend(page.get(key, []))
            return results
        except ClientError:
            raise  # auth failures, throttling — always propagate
        except Exception:
            pass  # method not pageable in this version — fall through

    # Direct single-page call
    resp = getattr(client, method)(**kwargs)
    return resp.get(key, [])
