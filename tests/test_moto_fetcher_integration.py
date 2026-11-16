"""
Integration test: real fetcher + real detectors against a moto-mocked AWS account.

Uses fake credentials only (AWS_ACCESS_KEY_ID=testing). Never touches real AWS.
Creates fake zombie resources in moto, then runs scanner.fetcher.fetch() + ALL_DETECTORS
against them. This validates that the fetcher correctly assembles a Snapshot from
real boto3 API response shapes, and that detectors correctly consume it.

Time travel: freezegun freezes 'now' to 2025-07-01 so resources created at 'now - 90 days'
in moto (via frozen creation time) trigger the 30-day / 24h / 90-day thresholds.

Known moto limitations (stated plainly, not worked around):
  - moto does not populate CloudWatch metrics for NAT Gateway / ALB / log groups
    from created resources. The NAT and ALB detectors that rely on CloudWatch
    traffic data therefore cannot be fully exercised here; they are covered
    by fixture-based unit tests in tests/detectors/. This test verifies only
    that the fetcher returns the resources without error and the detectors
    do not crash on the moto-shaped data.
  - moto's get_access_key_last_used returns LastUsedDate=null (never used).
    The IAM key detector correctly falls back to CreateDate; this test verifies
    that path.
  - moto's describe_snapshots returns OwnerId=123456789012 (the moto default
    account), NOT 111122223333. The snapshot orphan detector excludes only
    'amazon'/'aws-marketplace' owners, so moto-owned snapshots are still
    evaluated for orphan status.
"""

from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta

import boto3
import pytest
from freezegun import freeze_time
from moto import mock_aws

# Fake credentials — NEVER use real credentials
os.environ.setdefault("AWS_ACCESS_KEY_ID", "testing")
os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "xx")
os.environ.setdefault("AWS_DEFAULT_REGION", "us-east-1")

SCAN_TIME = datetime(2025, 7, 1, 10, 0, 0, tzinfo=UTC)
REGION = "us-east-1"


@pytest.fixture
def moto_env():
    """
    Start a moto mock_aws context, populate it, and keep it alive for the test.
    Tears down after the test.
    """
    create_time = SCAN_TIME - timedelta(days=90)

    session = boto3.Session(
        aws_access_key_id="testing",
        aws_secret_access_key="xx",
        region_name=REGION,
    )

    with mock_aws():
        with freeze_time(create_time):
            ec2 = session.client("ec2", region_name=REGION)
            iam = session.client("iam", region_name=REGION)
            elbv2 = session.client("elbv2", region_name=REGION)
            logs = session.client("logs", region_name=REGION)

            # ── VPC + subnet ────────────────────────────────────────────
            vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")
            vpc_id = vpc["Vpc"]["VpcId"]
            subnet = ec2.create_subnet(VpcId=vpc_id, CidrBlock="10.0.1.0/24")
            subnet_id = subnet["Subnet"]["SubnetId"]

            # ── Unattached EBS volume ────────────────────────────────────
            ec2.create_volume(
                AvailabilityZone=f"{REGION}a",
                Size=100,
                VolumeType="gp2",
                TagSpecifications=[
                    {"ResourceType": "volume", "Tags": [{"Key": "Name", "Value": "zombie-vol"}]}
                ],
            )

            # ── Orphaned snapshot (source volume deleted) ───────────────
            src_vol = ec2.create_volume(AvailabilityZone=f"{REGION}a", Size=50, VolumeType="gp3")
            ec2.create_snapshot(VolumeId=src_vol["VolumeId"], Description="orphaned backup")
            ec2.delete_volume(VolumeId=src_vol["VolumeId"])

            # ── Unassociated EIP ───────────────────────────────────────
            ec2.allocate_address(Domain="vpc")

            # ── Stopped EC2 instance ────────────────────────────────────
            inst = ec2.run_instances(
                ImageId="ami-test",
                InstanceType="t3.medium",
                SubnetId=subnet_id,
                MinCount=1,
                MaxCount=1,
                TagSpecifications=[
                    {"ResourceType": "instance", "Tags": [{"Key": "Name", "Value": "old-stopped"}]}
                ],
            )
            inst_id = inst["Instances"][0]["InstanceId"]
            ec2.stop_instances(InstanceIds=[inst_id])

            # ── Orphaned security group ────────────────────────────────
            ec2.create_security_group(
                GroupName="orphan-sg",
                Description="security group attached to nothing",
                VpcId=vpc_id,
            )

            # ── IAM user + unused access key ────────────────────────────
            iam.create_user(UserName="alice")
            iam.create_access_key(UserName="alice")

            # ── ALB with no targets ─────────────────────────────────────
            elbv2.create_load_balancer(Name="ghost-alb", Subnets=[subnet_id])

            # ── CloudWatch log group with no retention ──────────────────
            logs.create_log_group(logGroupName="/aws/lambda/forgotten")

        # Unfreeze before returning so the fetcher (which freezes SCAN_TIME
        # via the test decorator) can run with a valid signature timestamp.
        # The resources created above keep their frozen creation timestamps.

        yield session  # reuse the session fixture

    # mock_aws context exits here — teardown


# ── Test: fetcher assembles Snapshot from moto without error ──────────────────


@freeze_time(SCAN_TIME)
def test_fetcher_reads_moto_account(moto_env, default_config):
    from scanner.fetcher import fetch

    session = moto_env
    snap, skipped = fetch(session=session, regions=[REGION], config=default_config)

    assert skipped == 0
    assert snap.account_id  # moto returns a 12-digit id
    assert REGION in snap.regions
    assert REGION in snap.volumes
    assert REGION in snap.elastic_ips
    assert REGION in snap.instances
    assert REGION in snap.security_groups
    assert REGION in snap.snapshots_data
    assert len(snap.iam_access_keys) >= 1


# ── Test: detectors find the expected zombies in the moto snapshot ────────────


@freeze_time(SCAN_TIME)
def test_detectors_find_moto_zombies(moto_env, default_config):
    from scanner.detectors import ALL_DETECTORS
    from scanner.detectors.ebs_snapshots import detect as detect_snaps
    from scanner.detectors.ebs_volumes import detect as detect_volumes
    from scanner.detectors.ec2_stopped import detect as detect_stopped
    from scanner.detectors.elastic_ips import detect as detect_eips
    from scanner.detectors.iam_keys import detect as detect_keys
    from scanner.detectors.security_groups import detect as detect_sgs
    from scanner.fetcher import fetch

    session = moto_env
    snap, _ = fetch(session=session, regions=[REGION], config=default_config)

    tombstones = []
    for detector in ALL_DETECTORS:
        tombstones.extend(detector(snap, default_config))

    # ── Unattached EBS volume ──────────────────────────────────────────
    vol_results = detect_volumes(snap, default_config)
    assert len(vol_results) >= 1
    assert any(t.resource_type == "EC2::Volume" and t.cause == "abandoned" for t in vol_results)

    # ── Unassociated EIP ───────────────────────────────────────────────
    eip_results = detect_eips(snap, default_config)
    assert len(eip_results) >= 1
    assert all(t.cause == "idle, costs money" for t in eip_results)

    # ── Stopped EC2 instance older than 30 days ────────────────────────
    inst_results = detect_stopped(snap, default_config)
    assert len(inst_results) >= 1
    assert any(t.resource_type == "EC2::Instance" for t in inst_results)

    # ── Orphaned snapshot ─────────────────────────────────────────────
    snap_results = detect_snaps(snap, default_config)
    # The snapshot's source volume was deleted → orphaned.
    # NOTE: moto creates several auto snapshots for AMIs on first use.
    # Those have owner IDs that are NOT 'amazon'/'aws-marketplace', so the
    # snapshot detector may flag them too. We assert at least one is found.
    assert len(snap_results) >= 1

    # ── Unused IAM access key ─────────────────────────────────────────
    key_results = detect_keys(snap, default_config)
    assert len(key_results) >= 1
    assert any(t.resource_type == "IAM::AccessKey" for t in key_results)

    # ── Orphaned security group ───────────────────────────────────────
    sg_results = detect_sgs(snap, default_config)
    non_default = [t for t in sg_results if t.metadata.get("group_name") != "default"]
    assert len(non_default) >= 1


# ── Test: full report builds and validates from moto snapshot ─────────────────


@freeze_time(SCAN_TIME)
def test_full_report_from_moto(moto_env, default_config):
    from scanner.detectors import ALL_DETECTORS
    from scanner.fetcher import fetch
    from scanner.report import _report_to_dict, build_report

    session = moto_env
    snap, skipped = fetch(session=session, regions=[REGION], config=default_config)

    tombstones = []
    for detector in ALL_DETECTORS:
        tombstones.extend(detector(snap, default_config))

    report = build_report(
        tombstones=tombstones,
        snapshot=snap,
        scan_duration=0.01,
        demo=False,
    )
    report_dict = _report_to_dict(report)

    # Validate against the JSON schema
    import json
    from pathlib import Path

    import jsonschema

    schema = json.loads(Path("schema/report.schema.json").read_text())
    jsonschema.validate(report_dict, schema)

    assert report.summary.total_tombstones == len(tombstones)
    assert report.summary.total_tombstones >= 5  # at least the 6 we created


# ── Stated limitation: CloudWatch-based detectors ─────────────────────────────


@freeze_time(SCAN_TIME)
def test_cw_metric_limitation_documented(moto_env, default_config):
    """
    Plain statement of limitation: moto does NOT generate CloudWatch metric
    datapoints for NAT Gateway / ALB / log groups from the created resources.
    The fetcher calls get_metric_statistics and gets an empty Datapoints list.
    The NAT and ALB detectors therefore either skip (CW unavailable → skip)
    or flag based on target-group absence alone. This test documents that
    behavior rather than working around it.
    """
    from scanner.detectors.load_balancers import detect as detect_lb
    from scanner.detectors.log_groups import detect as detect_logs
    from scanner.detectors.nat_gateways import detect as detect_nat
    from scanner.fetcher import fetch

    session = moto_env
    snap, _ = fetch(session=session, regions=[REGION], config=default_config)

    # CW metrics dict is populated but values are empty lists
    cw = snap.cw_metrics.get(REGION, {})
    for key, datapoints in cw.items():
        assert datapoints == [], f"moto unexpectedly returned CW data for {key}"

    # ALB detector: no targets → flagged on target-group check alone
    lb_results = detect_lb(snap, default_config)
    assert any(t.resource_type == "ELB::LoadBalancer" for t in lb_results)

    # Log groups: storedBytes=0 + no CW data → flagged
    log_results = detect_logs(snap, default_config)
    assert len(log_results) >= 1

    # NAT detector: no NAT GW was created → empty result (correct)
    nat_results = detect_nat(snap, default_config)
    assert nat_results == []
