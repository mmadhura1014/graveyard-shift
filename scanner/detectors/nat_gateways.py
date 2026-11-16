"""
Detector: idle NAT Gateways.

Flags NAT Gateways whose total BytesOutToDestination over the last
nat_no_traffic_days days is below nat_min_bytes (default 1 MB).

Excludes gateways in 'deleting' or 'deleted' state.
Falls back gracefully when CloudWatch data is absent.

Cause:    "idle"
Severity: wasteful
"""

from __future__ import annotations

import logging
from datetime import UTC
from typing import Any

from scanner.models import Severity, Snapshot, Tombstone
from scanner.pricing import get_monthly_cost

log = logging.getLogger(__name__)


def detect(snapshot: Snapshot, config: dict[str, Any]) -> list[Tombstone]:
    min_bytes: int = config.get("nat_min_bytes", 1_048_576)
    now = snapshot.scanned_at
    if now.tzinfo is None:
        now = now.replace(tzinfo=UTC)

    tombstones: list[Tombstone] = []

    for region, gateways in snapshot.nat_gateways.items():
        cw_in_region = snapshot.cw_metrics.get(region, {})

        for gw in gateways:
            state = gw.get("State", "").lower()
            if state in ("deleting", "deleted"):
                continue

            gw_id = gw["NatGatewayId"]
            metric_key = f"{gw_id}:BytesOutToDestination"
            cw_data = cw_in_region.get(metric_key)

            if cw_data is None:
                log.warning(
                    "CloudWatch data unavailable for NAT Gateway %s (%s) — skipping",
                    gw_id,
                    region,
                )
                continue

            total_bytes = sum(dp.get("Sum", 0) for dp in cw_data)
            if total_bytes >= min_bytes:
                continue  # Active gateway

            name = _tag(gw, "Name")
            cost = get_monthly_cost("EC2::NatGateway", {}, region)

            raw_ct = gw.get("CreateTime", "")
            created_at = None
            if raw_ct:
                try:
                    from datetime import datetime

                    created_at = datetime.fromisoformat(raw_ct.replace("Z", "+00:00"))
                except (ValueError, TypeError):
                    pass

            tombstones.append(
                Tombstone(
                    resource_id=gw_id,
                    resource_name=name,
                    resource_type="EC2::NatGateway",
                    region=region,
                    account_id=snapshot.account_id,
                    cause="idle",
                    severity=Severity.WASTEFUL,
                    detected_at=now,
                    created_at=created_at,
                    estimated_monthly_cost=cost,
                    metadata={
                        "vpc_id": gw.get("VpcId", ""),
                        "subnet_id": gw.get("SubnetId", ""),
                        "total_bytes_14d": total_bytes,
                    },
                    exorcism_cli=(
                        f"aws ec2 delete-nat-gateway --nat-gateway-id {gw_id} --region {region}"
                        # Note: delete-nat-gateway has no --dry-run flag
                    ),
                    exorcism_tf=f'resource "aws_nat_gateway" "{_tf_name(name or gw_id)}" {{}}',
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
