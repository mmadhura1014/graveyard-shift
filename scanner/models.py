"""
Graveyard Shift — core data models.

All models are Pydantic v2.  The Snapshot dataclass holds raw boto3
response dicts; detectors receive it read-only and return list[Tombstone].
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

ACCOUNT_RE = re.compile(r"^\d{12}$")
REGION_RE = re.compile(r"^([a-z]{2}-[a-z]+-\d|global)$")


class Severity(StrEnum):
    HARMLESS = "harmless"  # green glow — no direct cost, low risk
    WASTEFUL = "wasteful"  # amber glow — wasting money
    RISKY = "risky"  # red glow  — security concern


# ---------------------------------------------------------------------------
# Tombstone
# ---------------------------------------------------------------------------


class Tombstone(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    resource_id: str
    resource_name: str | None = None
    resource_type: str
    region: str
    account_id: str
    cause: str
    severity: Severity
    detected_at: datetime
    created_at: datetime | None = None
    estimated_monthly_cost: Decimal = Decimal("0")
    metadata: dict[str, Any] = Field(default_factory=dict)
    exorcism_cli: str
    exorcism_tf: str = ""

    @field_validator("estimated_monthly_cost")
    @classmethod
    def cost_non_negative(cls, v: Decimal) -> Decimal:
        if v < 0:
            raise ValueError(f"estimated_monthly_cost must be >= 0, got {v}")
        return v

    @field_validator("account_id")
    @classmethod
    def valid_account_id(cls, v: str) -> str:
        if not ACCOUNT_RE.match(v):
            raise ValueError(f"account_id must be a 12-digit string, got {v!r}")
        return v

    @field_validator("resource_id", "resource_type", "cause", "exorcism_cli")
    @classmethod
    def non_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("field must be non-empty")
        return v


# ---------------------------------------------------------------------------
# Report summary
# ---------------------------------------------------------------------------


class ReportSummary(BaseModel):
    model_config = ConfigDict(frozen=True)

    total_tombstones: int
    estimated_monthly_cost: Decimal
    undead_credentials_count: int
    by_severity: dict[str, int]
    by_type: dict[str, int]

    @field_validator("total_tombstones", "undead_credentials_count")
    @classmethod
    def non_negative_int(cls, v: int) -> int:
        if v < 0:
            raise ValueError("count must be >= 0")
        return v

    @field_validator("estimated_monthly_cost")
    @classmethod
    def cost_non_negative(cls, v: Decimal) -> Decimal:
        if v < 0:
            raise ValueError("estimated_monthly_cost must be >= 0")
        return v

    @classmethod
    def from_tombstones(cls, tombstones: list[Tombstone]) -> ReportSummary:
        total_cost = sum(t.estimated_monthly_cost for t in tombstones)
        undead = sum(1 for t in tombstones if t.resource_type == "IAM::AccessKey")
        by_sev: dict[str, int] = {"harmless": 0, "wasteful": 0, "risky": 0}
        by_type: dict[str, int] = {}
        for t in tombstones:
            by_sev[t.severity.value] += 1
            by_type[t.resource_type] = by_type.get(t.resource_type, 0) + 1
        return cls(
            total_tombstones=len(tombstones),
            estimated_monthly_cost=total_cost,
            undead_credentials_count=undead,
            by_severity=by_sev,
            by_type=by_type,
        )


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

SCHEMA_VERSION = "1.0"


class Report(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: str = SCHEMA_VERSION
    generated_at: datetime
    demo: bool
    account_id: str
    regions_scanned: list[str]
    scan_duration_seconds: float
    tombstones: list[Tombstone]
    summary: ReportSummary

    @field_validator("account_id")
    @classmethod
    def valid_account_id(cls, v: str) -> str:
        if not ACCOUNT_RE.match(v):
            raise ValueError(f"account_id must be a 12-digit string, got {v!r}")
        return v

    @field_validator("scan_duration_seconds")
    @classmethod
    def non_negative_duration(cls, v: float) -> float:
        if v < 0:
            raise ValueError("scan_duration_seconds must be >= 0")
        return v

    @model_validator(mode="after")
    def summary_consistent(self) -> Report:
        expected = len(self.tombstones)
        if self.summary.total_tombstones != expected:
            raise ValueError(
                f"summary.total_tombstones={self.summary.total_tombstones} "
                f"does not match len(tombstones)={expected}"
            )
        return self


# ---------------------------------------------------------------------------
# Snapshot — raw boto3 response containers (mutable dataclass, not Pydantic)
# ---------------------------------------------------------------------------


@dataclass
class Snapshot:
    """
    Holds raw boto3 API response dicts for one scan run.
    Detectors receive this and MUST NOT modify it.
    All per-region dicts are keyed by region string.
    """

    account_id: str
    regions: list[str]
    scanned_at: datetime

    # Per-region
    volumes: dict[str, list[dict]] = field(default_factory=dict)
    snapshots_data: dict[str, list[dict]] = field(default_factory=dict)
    elastic_ips: dict[str, list[dict]] = field(default_factory=dict)
    load_balancers: dict[str, list[dict]] = field(default_factory=dict)
    target_groups: dict[str, list[dict]] = field(default_factory=dict)
    target_health: dict[str, dict[str, list[dict]]] = field(default_factory=dict)
    nat_gateways: dict[str, list[dict]] = field(default_factory=dict)
    instances: dict[str, list[dict]] = field(default_factory=dict)
    security_groups: dict[str, list[dict]] = field(default_factory=dict)
    enis: dict[str, list[dict]] = field(default_factory=dict)
    log_groups: dict[str, list[dict]] = field(default_factory=dict)
    # cw_metrics keyed by region → metric_key → list of datapoints
    cw_metrics: dict[str, dict[str, list[dict]]] = field(default_factory=dict)

    # Global (no region key)
    iam_users: list[dict] = field(default_factory=list)
    iam_access_keys: list[dict] = field(default_factory=list)
