"""
Detector: CloudWatch log groups that are hoarders.

Flags log groups that have ALL of:
  - No retention policy (retentionInDays is null)
  - No metric filters (metricFilterCount == 0)
  - No recent log ingestion (IncomingLogEvents total over last 30 days == 0,
    or storedBytes == 0 and no CW data)

Cause:    "hoarder"
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

    for region, groups in snapshot.log_groups.items():
        cw_in_region = snapshot.cw_metrics.get(region, {})

        for lg in groups:
            # Must have no retention policy
            if lg.get("retentionInDays") is not None:
                continue

            # Must have no metric filters
            if lg.get("metricFilterCount", 0) > 0:
                continue

            log_group_name = lg["logGroupName"]
            stored_bytes = lg.get("storedBytes", 0)

            # Check ingestion: look for IncomingLogEvents CW metric
            metric_key = f"{log_group_name}:IncomingLogEvents"
            cw_data = cw_in_region.get(metric_key)

            if cw_data is not None:
                total_events = sum(dp.get("Sum", 0) for dp in cw_data)
                if total_events > 0:
                    continue  # Active log group
            else:
                # No CW data — treat storedBytes == 0 as confirmation of quiet
                if stored_bytes > 0:
                    # Has data but no CW metric — be conservative, skip
                    log.warning(
                        "No CW IncomingLogEvents data for %s (%s) with storedBytes=%d — skipping",
                        log_group_name,
                        region,
                        stored_bytes,
                    )
                    continue
                # storedBytes == 0 and no CW data → flag

            cost = get_monthly_cost(
                "CWLogs::LogGroup",
                {"stored_bytes": stored_bytes},
                region,
            )

            tombstones.append(
                Tombstone(
                    resource_id=log_group_name,
                    resource_name=log_group_name,
                    resource_type="CWLogs::LogGroup",
                    region=region,
                    account_id=snapshot.account_id,
                    cause="hoarder",
                    severity=Severity.WASTEFUL,
                    detected_at=now,
                    created_at=None,
                    estimated_monthly_cost=cost,
                    metadata={
                        "log_group_name": log_group_name,
                        "stored_bytes": stored_bytes,
                    },
                    exorcism_cli=(
                        f"aws logs delete-log-group "
                        f"--log-group-name {log_group_name} "
                        f"--region {region}"
                    ),
                    exorcism_tf=f'resource "aws_cloudwatch_log_group" "{_tf_name(log_group_name)}" {{}}',
                )
            )

    return tombstones


def _tf_name(raw: str) -> str:
    import re

    return re.sub(r"[^a-zA-Z0-9_]", "_", raw)[:64]
