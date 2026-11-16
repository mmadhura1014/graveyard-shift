"""
Detector: stale IAM access keys.

Flags access keys that have not been used for iam_key_unused_days (default 90)
days, or were never used and were created more than that many days ago.

Active stale keys → severity RISKY (security concern).
Inactive stale keys → severity WASTEFUL (already disabled; still present).

Contributes to summary.undead_credentials_count.

Cause:    "undead credentials"
Region:   "global" (IAM is a global service)
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from scanner.models import Severity, Snapshot, Tombstone

log = logging.getLogger(__name__)


def detect(snapshot: Snapshot, config: dict[str, Any]) -> list[Tombstone]:
    threshold_days: int = config.get("iam_key_unused_days", 90)
    now = snapshot.scanned_at
    if now.tzinfo is None:
        now = now.replace(tzinfo=UTC)

    tombstones: list[Tombstone] = []

    for key_info in snapshot.iam_access_keys:
        username = key_info.get("UserName", "unknown")
        key_id = key_info.get("AccessKeyId", "")
        status = key_info.get("Status", "Active")

        # Determine the last-activity date
        last_used_raw = key_info.get("LastUsedDate")
        create_raw = key_info.get("CreateDate", "")

        last_used: datetime | None = None
        if last_used_raw:
            try:
                last_used = datetime.fromisoformat(str(last_used_raw).replace("Z", "+00:00"))
            except (ValueError, TypeError):
                last_used = None

        created_at: datetime | None = None
        if create_raw:
            try:
                created_at = datetime.fromisoformat(str(create_raw).replace("Z", "+00:00"))
            except (ValueError, TypeError):
                created_at = None

        # Reference date: last used if available, otherwise creation date
        reference = last_used if last_used is not None else created_at
        if reference is None:
            log.warning("Cannot determine age for key %s (user %s) — skipping", key_id, username)
            continue

        idle_days = (now - reference).days
        if idle_days < threshold_days:
            continue

        severity = Severity.RISKY if status == "Active" else Severity.WASTEFUL

        tombstones.append(
            Tombstone(
                resource_id=key_id,
                resource_name=f"{username}/{key_id}",
                resource_type="IAM::AccessKey",
                region="global",
                account_id=snapshot.account_id,
                cause="undead credentials",
                severity=severity,
                detected_at=now,
                created_at=created_at,
                estimated_monthly_cost=Decimal("0"),
                metadata={
                    "username": username,
                    "key_id": key_id,
                    "status": status,
                    "idle_days": idle_days,
                    "last_used_date": last_used.isoformat() if last_used else None,
                },
                exorcism_cli=(
                    f"aws iam delete-access-key --access-key-id {key_id} --user-name {username}"
                ),
                exorcism_tf=(
                    f'resource "aws_iam_access_key" "{_tf_name(username)}_{_tf_name(key_id)}" {{}}'
                ),
            )
        )

    return tombstones


def _tf_name(raw: str) -> str:
    import re

    return re.sub(r"[^a-zA-Z0-9_]", "_", raw)[:32]
