"""
Detector: unattached EBS volumes.
(Verified: regex/UTC fix from moto test retained; pricing checked 2026-11.)

Flags volumes in 'available' state (not attached to any instance) that
were created more than config['ebs_volume_grace_period_hours'] hours ago.

Cause:    "abandoned"
Severity: wasteful
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from scanner.models import Severity, Snapshot, Tombstone
from scanner.pricing import get_monthly_cost


def detect(snapshot: Snapshot, config: dict[str, Any]) -> list[Tombstone]:
    """
    Pure function: receives a snapshot, returns zombie tombstones.
    Does NOT modify the snapshot.
    """
    grace_hours: int = config.get("ebs_volume_grace_period_hours", 24)
    now = (
        snapshot.scanned_at.replace(tzinfo=UTC)
        if snapshot.scanned_at.tzinfo is None
        else snapshot.scanned_at
    )
    tombstones: list[Tombstone] = []

    for region, volumes in snapshot.volumes.items():
        for vol in volumes:
            if vol.get("State") != "available":
                continue

            # Parse creation time
            raw_ct = vol.get("CreateTime", "")
            try:
                created_at = _parse_dt(raw_ct)
            except (ValueError, TypeError):
                created_at = None

            # Grace-period check
            if created_at is not None:
                age_hours = (now - created_at).total_seconds() / 3600
                if age_hours < grace_hours:
                    continue

            volume_id = vol["VolumeId"]
            volume_type = vol.get("VolumeType", "gp2")
            size_gib = vol.get("Size", 0)
            name = _tag(vol, "Name")

            meta = {
                "size_gib": size_gib,
                "volume_type": volume_type,
                "availability_zone": vol.get("AvailabilityZone", ""),
            }
            cost = get_monthly_cost(
                "EC2::Volume",
                {"volume_type": volume_type, "size_gib": size_gib},
                region,
            )

            tombstones.append(
                Tombstone(
                    resource_id=volume_id,
                    resource_name=name,
                    resource_type="EC2::Volume",
                    region=region,
                    account_id=snapshot.account_id,
                    cause="abandoned",
                    severity=Severity.WASTEFUL,
                    detected_at=now,
                    created_at=created_at,
                    estimated_monthly_cost=cost,
                    metadata=meta,
                    exorcism_cli=(
                        f"aws ec2 delete-volume --volume-id {volume_id} --region {region} --dry-run"
                    ),
                    exorcism_tf=f'resource "aws_ebs_volume" "{_tf_name(name or volume_id)}" {{}}',
                )
            )

    return tombstones


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _parse_dt(value: str) -> datetime:
    """Parse an ISO-8601 string to a UTC-aware datetime."""
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt


def _tag(resource: dict, key: str) -> str | None:
    for t in resource.get("Tags", []):
        if t.get("Key") == key:
            return t.get("Value")
    return None


def _tf_name(raw: str) -> str:
    """Sanitise a string for use as a Terraform resource label."""
    import re

    return re.sub(r"[^a-zA-Z0-9_]", "_", raw)[:64]
