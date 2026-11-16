"""
Detector: unassociated Elastic IPs.

AWS charges for EIPs that are allocated but not associated with a running
resource.  Every unassociated EIP costs ~$3.65/month.

Cause:    "idle, costs money"
Severity: wasteful
"""

from __future__ import annotations

from datetime import UTC
from typing import Any

from scanner.models import Severity, Snapshot, Tombstone
from scanner.pricing import get_monthly_cost


def detect(snapshot: Snapshot, config: dict[str, Any]) -> list[Tombstone]:
    """Pure function: flags EIPs with no AssociationId."""
    now = snapshot.scanned_at
    if now.tzinfo is None:
        now = now.replace(tzinfo=UTC)

    tombstones: list[Tombstone] = []

    for region, addresses in snapshot.elastic_ips.items():
        for addr in addresses:
            # If AssociationId is present and non-empty, the EIP is in use
            if addr.get("AssociationId"):
                continue

            alloc_id = addr["AllocationId"]
            public_ip = addr.get("PublicIp", "")
            name = _tag(addr, "Name")

            cost = get_monthly_cost("EC2::EIP", {}, region)

            tombstones.append(
                Tombstone(
                    resource_id=alloc_id,
                    resource_name=name,
                    resource_type="EC2::EIP",
                    region=region,
                    account_id=snapshot.account_id,
                    cause="idle, costs money",
                    severity=Severity.WASTEFUL,
                    detected_at=now,
                    created_at=None,
                    estimated_monthly_cost=cost,
                    metadata={"public_ip": public_ip},
                    exorcism_cli=(
                        f"aws ec2 release-address --allocation-id {alloc_id} "
                        f"--region {region} --dry-run"
                    ),
                    exorcism_tf=f'resource "aws_eip" "{_tf_name(name or alloc_id)}" {{}}',
                )
            )

    return tombstones


def _tag(resource: dict, key: str) -> str | None:
    for t in resource.get("Tags", []):
        if t.get("Key") == key:
            return t.get("Value")
    return None


def _tf_name(raw: str) -> str:
    import re

    return re.sub(r"[^a-zA-Z0-9_]", "_", raw)[:64]
