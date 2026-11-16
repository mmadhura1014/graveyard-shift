#!/usr/bin/env python3
"""
Run the REAL fetcher + detectors against an in-process moto mock account.

Creates fake zombie resources, then runs the scanner against them.
Fake credentials only — never touches real AWS.

Usage:
    python scripts/moto_demo_scan.py --out report.json
"""

from __future__ import annotations

import argparse
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path

# Fake credentials BEFORE importing boto3 / scanner
os.environ.setdefault("AWS_ACCESS_KEY_ID", "testing")
os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "xx")
os.environ.setdefault("AWS_DEFAULT_REGION", "us-east-1")

import boto3
from freezegun import freeze_time
from moto import mock_aws

SCAN_TIME = datetime(2025, 7, 1, 10, 0, 0, tzinfo=UTC)
CREATE_TIME = SCAN_TIME - timedelta(days=90)
REGION = "us-east-1"


def populate_account(session: boto3.Session) -> None:
    """Create fake zombie resources in the moto account."""
    ec2 = session.client("ec2", region_name=REGION)
    iam = session.client("iam", region_name=REGION)
    elbv2 = session.client("elbv2", region_name=REGION)
    logs = session.client("logs", region_name=REGION)

    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")
    vpc_id = vpc["Vpc"]["VpcId"]
    subnet = ec2.create_subnet(VpcId=vpc_id, CidrBlock="10.0.1.0/24")
    subnet_id = subnet["Subnet"]["SubnetId"]

    # Unattached EBS volume
    ec2.create_volume(
        AvailabilityZone=f"{REGION}a",
        Size=100,
        VolumeType="gp2",
        TagSpecifications=[
            {"ResourceType": "volume", "Tags": [{"Key": "Name", "Value": "zombie-vol"}]}
        ],
    )

    # Orphaned snapshot
    src_vol = ec2.create_volume(AvailabilityZone=f"{REGION}a", Size=50, VolumeType="gp3")
    ec2.create_snapshot(VolumeId=src_vol["VolumeId"], Description="orphaned backup")
    ec2.delete_volume(VolumeId=src_vol["VolumeId"])

    # Unassociated EIP
    ec2.allocate_address(Domain="vpc")

    # Stopped EC2 instance
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
    ec2.stop_instances(InstanceIds=[inst["Instances"][0]["InstanceId"]])

    # Orphaned security group
    ec2.create_security_group(
        GroupName="orphan-sg", Description="attached to nothing", VpcId=vpc_id
    )

    # IAM user + unused access key
    iam.create_user(UserName="alice")
    iam.create_access_key(UserName="alice")

    # ALB with no targets
    elbv2.create_load_balancer(Name="ghost-alb", Subnets=[subnet_id])

    # CloudWatch log group with no retention
    logs.create_log_group(logGroupName="/aws/lambda/forgotten")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Scan a moto-mocked account (fake creds, no real AWS)."
    )
    parser.add_argument("--out", default="/tmp/graveyard-live.json", help="Output report path")
    args = parser.parse_args()

    session = boto3.Session(
        aws_access_key_id="testing",
        aws_secret_access_key="xx",
        region_name=REGION,
    )

    from scanner.config import load_config
    from scanner.detectors import ALL_DETECTORS
    from scanner.fetcher import fetch
    from scanner.report import build_report, write_report

    config = load_config()

    with mock_aws():
        with freeze_time(CREATE_TIME):
            populate_account(session)

        with freeze_time(SCAN_TIME):
            snap, skipped = fetch(session=session, regions=[REGION], config=config)

            # moto ignores the OwnerIds=["self"] filter and returns ~1300 built-in
            # AMI snapshots. Real AWS honours it, so keep only snapshots owned by
            # the mock account to mirror what a real scan would return.
            for region, snaps in snap.snapshots_data.items():
                snap.snapshots_data[region] = [
                    s for s in snaps if s.get("OwnerId") == snap.account_id
                ]

            tombstones = []
            for detector in ALL_DETECTORS:
                tombstones.extend(detector(snap, config))

            report = build_report(
                tombstones=tombstones,
                snapshot=snap,
                scan_duration=0.01,
                demo=False,
            )
            out_path = Path(args.out)
            write_report(report, out_path)

            print(f"✓ moto live-mode report written to {out_path}")
            print(f"  Account ID: {report.account_id} (moto default)")
            print(f"  Tombstones: {report.summary.total_tombstones}")
            print(
                f"  Estimated haunting cost: ${report.summary.estimated_monthly_cost:.2f}/mo (estimated)"
            )
            print(f"  Undead credentials: {report.summary.undead_credentials_count}")
            print("  (fake credentials, in-process moto mock — no real AWS calls)")


if __name__ == "__main__":
    main()
