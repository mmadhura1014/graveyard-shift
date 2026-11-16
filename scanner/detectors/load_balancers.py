"""
Detector: idle ALB / NLB load balancers.

Flags a load balancer when:
  (a) it has no registered targets in any target group, OR
  (b) it has targets but zero traffic over the last lb_no_traffic_days days
      (ALB: RequestCount metric; NLB: ActiveFlowCount metric).

CloudWatch data is optional — if unavailable the detector falls back to
the target-group check only and logs a warning.

Cause:    "lonely"
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
    now = snapshot.scanned_at
    if now.tzinfo is None:
        now = now.replace(tzinfo=UTC)

    tombstones: list[Tombstone] = []

    for region, lbs in snapshot.load_balancers.items():
        tgs_in_region = snapshot.target_groups.get(region, [])
        health_in_region = snapshot.target_health.get(region, {})
        cw_in_region = snapshot.cw_metrics.get(region, {})

        # Build: lb_arn → list[target_group_arn]
        lb_to_tg_arns: dict[str, list[str]] = {}
        for tg in tgs_in_region:
            for lb_arn in tg.get("LoadBalancerArns", []):
                lb_to_tg_arns.setdefault(lb_arn, []).append(tg["TargetGroupArn"])

        for lb in lbs:
            lb_arn = lb["LoadBalancerArn"]
            lb_name = lb["LoadBalancerName"]
            lb_type_raw = lb.get("Type", "application").lower()
            lb_type = "ALB" if lb_type_raw == "application" else "NLB"

            tg_arns = lb_to_tg_arns.get(lb_arn, [])

            # Check (a): no target groups at all, or all target groups empty
            has_targets = False
            for tg_arn in tg_arns:
                healths = health_in_region.get(tg_arn, [])
                if healths:
                    has_targets = True
                    break

            if not tg_arns or not has_targets:
                reason = "no registered targets"
            else:
                # Check (b): traffic in CW
                metric_key = (
                    f"{lb_name}:RequestCount" if lb_type == "ALB" else f"{lb_name}:ActiveFlowCount"
                )
                cw_data = cw_in_region.get(metric_key)
                if cw_data is None:
                    # CW unavailable — fall back to target check only
                    log.warning(
                        "CloudWatch data unavailable for %s (%s) — "
                        "falling back to target-group check only",
                        lb_name,
                        region,
                    )
                    # Has targets and no CW → assume active
                    continue
                total_traffic = sum(dp.get("Sum", 0) for dp in cw_data)
                if total_traffic > 0:
                    continue  # Active LB — not a zombie
                reason = "zero traffic over 14 days"

            cost = get_monthly_cost(
                "ELB::LoadBalancer",
                {"lb_type": lb_type},
                region,
            )

            raw_ct = lb.get("CreatedTime", "")
            created_at = None
            if raw_ct:
                try:
                    from datetime import datetime

                    created_at = datetime.fromisoformat(raw_ct.replace("Z", "+00:00"))
                except (ValueError, TypeError):
                    pass

            tombstones.append(
                Tombstone(
                    resource_id=lb_arn,
                    resource_name=lb_name,
                    resource_type="ELB::LoadBalancer",
                    region=region,
                    account_id=snapshot.account_id,
                    cause="lonely",
                    severity=Severity.WASTEFUL,
                    detected_at=now,
                    created_at=created_at,
                    estimated_monthly_cost=cost,
                    metadata={
                        "lb_type": lb_type,
                        "dns_name": lb.get("DNSName", ""),
                        "reason": reason,
                    },
                    exorcism_cli=(
                        f"aws elbv2 delete-load-balancer "
                        f"--load-balancer-arn {lb_arn} "
                        f"--region {region}"
                    ),
                    exorcism_tf=f'resource "aws_lb" "{_tf_name(lb_name)}" {{}}',
                )
            )

    return tombstones


def _tf_name(raw: str) -> str:
    import re

    return re.sub(r"[^a-zA-Z0-9_]", "_", raw)[:64]
