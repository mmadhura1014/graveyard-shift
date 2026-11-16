"""
Detector: orphaned EBS snapshots (source volume no longer exists).

Cause:    "orphaned"
Severity: wasteful
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from scanner.models import Severity, Snapshot, Tombstone
from scanner.pricing import get_monthly_cost


def detect(snapshot: Snapshot, config: dict[str, Any]) -> list[Tombstone]:
    """
    Pure function: flags snapshots whose VolumeId does not appear in the
    account's volume list.  AWS-owned snapshots (owner amazon / aws-marketplace)
    are excluded.
    """
    now = snapshot.scanned_at
    if now.tzinfo is None:
        now = now.replace(tzinfo=UTC)

    # Collect all known volume IDs across all regions
    known_volume_ids: set[str] = set()
    for vols in snapshot.volumes.values():
        for vol in vols:
            known_volume_ids.add(vol["VolumeId"])

    tombstones: list[Tombstone] = []

    for region, snaps in snapshot.snapshots_data.items():
        for snap in snaps:
            # Exclude AWS-owned snapshots
            owner = snap.get("OwnerId", "")
            if owner in ("amazon", "aws-marketplace"):
                continue

            volume_id = snap.get("VolumeId", "")
            if volume_id in known_volume_ids:
                continue  # source volume still exists

            snap_id = snap["SnapshotId"]
            size_gib = snap.get("VolumeSize", 0)
            name = _tag(snap, "Name") or snap.get("Description") or None

            raw_ct = snap.get("StartTime", "")
            try:
                created_at = datetime.fromisoformat(raw_ct.replace("Z", "+00:00"))
            except (ValueError, TypeError):
                created_at = None

            cost = get_monthly_cost(
                "EC2::Snapshot",
                {"size_gib": size_gib},
                region,
            )

            tombstones.append(
                Tombstone(
                    resource_id=snap_id,
                    resource_name=name,
                    resource_type="EC2::Snapshot",
                    region=region,
                    account_id=snapshot.account_id,
                    cause="orphaned",
                    severity=Severity.WASTEFUL,
                    detected_at=now,
                    created_at=created_at,
                    estimated_monthly_cost=cost,
                    metadata={
                        "size_gib": size_gib,
                        "source_volume_id": volume_id,
                        "owner_id": owner,
                    },
                    exorcism_cli=(
                        f"aws ec2 delete-snapshot --snapshot-id {snap_id} "
                        f"--region {region} --dry-run"
                    ),
                    exorcism_tf=f'resource "aws_ebs_snapshot" "{_tf_name(snap_id)}" {{}}',
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
