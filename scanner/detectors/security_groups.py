"""
Detector: orphaned security groups.

Flags security groups not referenced by any ENI, EC2 instance, or ELB.
The VPC 'default' security group is excluded (it cannot be deleted).

Cause:    "forgotten"
Severity: harmless
"""

from __future__ import annotations

from datetime import UTC
from decimal import Decimal
from typing import Any

from scanner.models import Severity, Snapshot, Tombstone


def detect(snapshot: Snapshot, config: dict[str, Any]) -> list[Tombstone]:
    now = snapshot.scanned_at
    if now.tzinfo is None:
        now = now.replace(tzinfo=UTC)

    tombstones: list[Tombstone] = []

    for region, sgs in snapshot.security_groups.items():
        # Build the set of referenced group IDs in this region
        referenced = _referenced_sg_ids(snapshot, region)

        for sg in sgs:
            # Never flag the default SG — it cannot be deleted
            if sg.get("GroupName", "").lower() == "default":
                continue

            group_id = sg["GroupId"]
            if group_id in referenced:
                continue

            group_name = sg.get("GroupName", "")
            vpc_id = sg.get("VpcId", "")
            name = _tag(sg, "Name") or group_name or None

            tombstones.append(
                Tombstone(
                    resource_id=group_id,
                    resource_name=name,
                    resource_type="EC2::SecurityGroup",
                    region=region,
                    account_id=snapshot.account_id,
                    cause="forgotten",
                    severity=Severity.HARMLESS,
                    detected_at=now,
                    created_at=None,
                    estimated_monthly_cost=Decimal("0"),
                    metadata={
                        "vpc_id": vpc_id,
                        "group_name": group_name,
                    },
                    exorcism_cli=(
                        f"aws ec2 delete-security-group "
                        f"--group-id {group_id} "
                        f"--region {region} --dry-run"
                    ),
                    exorcism_tf=f'resource "aws_security_group" "{_tf_name(group_name or group_id)}" {{}}',
                )
            )

    return tombstones


def _referenced_sg_ids(snapshot: Snapshot, region: str) -> set[str]:
    """Return the set of security group IDs actively in use in this region."""
    referenced: set[str] = set()

    # From ENIs
    for eni in snapshot.enis.get(region, []):
        for g in eni.get("Groups", []):
            referenced.add(g["GroupId"])

    # From EC2 instances
    for inst in _iter_instances(snapshot.instances.get(region, [])):
        for g in inst.get("SecurityGroups", []):
            referenced.add(g["GroupId"])

    # From load balancers (security groups field on ALBs)
    for lb in snapshot.load_balancers.get(region, []):
        for gid in lb.get("SecurityGroups", []):
            referenced.add(gid)

    return referenced


def _iter_instances(reservations: list[dict]):
    for item in reservations:
        if "Instances" in item:
            yield from item["Instances"]
        else:
            yield item


def _tag(resource: dict, key: str) -> str | None:
    for t in resource.get("Tags", []):
        if t.get("Key") == key:
            return t.get("Value")
    return None


def _tf_name(raw: str) -> str:
    import re

    return re.sub(r"[^a-zA-Z0-9_]", "_", raw)[:64]
