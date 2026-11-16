"""
Shared pytest fixtures for Graveyard Shift tests.
"""

from __future__ import annotations

import copy
import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from scanner.config import DEFAULT_CONFIG
from scanner.models import Snapshot

SEED_DIR = Path(__file__).parent.parent / "seed"


@pytest.fixture
def default_config() -> dict:
    return copy.deepcopy(DEFAULT_CONFIG)


@pytest.fixture
def seed_snapshot() -> Snapshot:
    """Load the synthetic seed snapshot from seed/snapshot.json."""
    raw = json.loads((SEED_DIR / "snapshot.json").read_text())
    return Snapshot(
        account_id=raw["account_id"],
        regions=raw["regions"],
        scanned_at=datetime.fromisoformat(raw["scanned_at"].replace("Z", "+00:00")),
        volumes=raw.get("volumes", {}),
        snapshots_data=raw.get("snapshots_data", {}),
        elastic_ips=raw.get("elastic_ips", {}),
        load_balancers=raw.get("load_balancers", {}),
        target_groups=raw.get("target_groups", {}),
        target_health=raw.get("target_health", {}),
        nat_gateways=raw.get("nat_gateways", {}),
        instances=raw.get("instances", {}),
        security_groups=raw.get("security_groups", {}),
        enis=raw.get("enis", {}),
        log_groups=raw.get("log_groups", {}),
        cw_metrics=raw.get("cw_metrics", {}),
        iam_users=raw.get("iam_users", []),
        iam_access_keys=raw.get("iam_access_keys", []),
    )


@pytest.fixture
def empty_snapshot() -> Snapshot:
    """A snapshot with no resources — detectors must return [] without raising."""
    return Snapshot(
        account_id="111122223333",
        regions=["us-east-1"],
        scanned_at=datetime(2025, 7, 1, 10, 0, 0, tzinfo=UTC),
    )
