"""
Detector: EC2 instances stopped for >= ec2_stopped_days days.

Stopped instances still accrue EBS storage charges for every attached volume.

StateTransitionReason format: "User initiated (2024-11-01 10:23:45 GMT)"
Falls back to LaunchTime if the timestamp can't be parsed.

Cause:    "dead but still billed for EBS"
Severity: wasteful
"""

from __future__ import annotations

import logging
import re
from datetime import UTC, datetime
from typing import Any

from scanner.models import Severity, Snapshot, Tombstone
from scanner.pricing import get_monthly_cost

log = logging.getLogger(__name__)

# "User initiated (2024-11-01 10:23:45 GMT)"  — AWS uses both GMT and UTC suffixes
_STOP_TIME_RE = re.compile(r"\((\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})\s+(?:GMT|UTC)\)")


def detect(snapshot: Snapshot, config: dict[str, Any]) -> list[Tombstone]:
    threshold_days: int = config.get("ec2_stopped_days", 30)
    now = snapshot.scanned_at
    if now.tzinfo is None:
        now = now.replace(tzinfo=UTC)

    tombstones: list[Tombstone] = []

    for region, reservations in snapshot.instances.items():
        for inst in _iter_instances(reservations):
            state = inst.get("State", {}).get("Name", "")
            if state != "stopped":
                continue

            stop_time = _parse_stop_time(inst.get("StateTransitionReason", ""))
            if stop_time is None:
                # Fall back to launch time — conservative: may under-report
                raw_lt = inst.get("LaunchTime", "")
                if raw_lt:
                    try:
                        stop_time = datetime.fromisoformat(raw_lt.replace("Z", "+00:00"))
                    except (ValueError, TypeError):
                        log.warning(
                            "Cannot determine stop time for %s — skipping",
                            inst.get("InstanceId", "?"),
                        )
                        continue
                else:
                    continue

            stopped_days = (now - stop_time).days
            if stopped_days < threshold_days:
                continue

            inst_id = inst["InstanceId"]
            inst_type = inst.get("InstanceType", "unknown")
            name = _tag(inst, "Name")

            # Sum EBS storage attached to this instance
            ebs_size_gib = _total_ebs_gib(inst, snapshot.volumes.get(region, []))

            cost = get_monthly_cost(
                "EC2::Instance",
                {"ebs_size_gib": ebs_size_gib},
                region,
            )

            raw_lt = inst.get("LaunchTime", "")
            created_at = None
            if raw_lt:
                try:
                    created_at = datetime.fromisoformat(raw_lt.replace("Z", "+00:00"))
                except (ValueError, TypeError):
                    pass

            tombstones.append(
                Tombstone(
                    resource_id=inst_id,
                    resource_name=name,
                    resource_type="EC2::Instance",
                    region=region,
                    account_id=snapshot.account_id,
                    cause="dead but still billed for EBS",
                    severity=Severity.WASTEFUL,
                    detected_at=now,
                    created_at=created_at,
                    estimated_monthly_cost=cost,
                    metadata={
                        "instance_type": inst_type,
                        "ebs_size_gib": ebs_size_gib,
                        "stopped_days": stopped_days,
                    },
                    exorcism_cli=(
                        f"aws ec2 terminate-instances "
                        f"--instance-ids {inst_id} "
                        f"--region {region} --dry-run"
                    ),
                    exorcism_tf=f'resource "aws_instance" "{_tf_name(name or inst_id)}" {{}}',
                )
            )

    return tombstones


# ── helpers ───────────────────────────────────────────────────────────────────


def _iter_instances(reservations: list[dict]):
    """Flatten reservations → instances."""
    for item in reservations:
        # boto3 wraps instances in Reservations; seed data is flat list of instances
        if "Instances" in item:
            yield from item["Instances"]
        else:
            yield item


def _parse_stop_time(reason: str) -> datetime | None:
    """Extract UTC datetime from StateTransitionReason string."""
    m = _STOP_TIME_RE.search(reason)
    if not m:
        return None
    try:
        dt = datetime.strptime(m.group(1), "%Y-%m-%d %H:%M:%S")
        return dt.replace(tzinfo=UTC)
    except ValueError:
        return None


def _total_ebs_gib(inst: dict, region_volumes: list[dict]) -> int:
    """Sum GiB of all EBS volumes attached to this instance."""
    vol_ids = {
        bdm["Ebs"]["VolumeId"] for bdm in inst.get("BlockDeviceMappings", []) if "Ebs" in bdm
    }
    vol_map = {v["VolumeId"]: v.get("Size", 0) for v in region_volumes}
    return sum(vol_map.get(vid, 0) for vid in vol_ids)


def _tag(resource: dict, key: str) -> str | None:
    for t in resource.get("Tags", []):
        if t.get("Key") == key:
            return t.get("Value")
    return None


def _tf_name(raw: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_]", "_", raw)[:64]
