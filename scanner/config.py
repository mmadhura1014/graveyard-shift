"""
Graveyard Shift — detection thresholds and configuration.

All thresholds live here with their defaults.  Pass --config <path> on the
CLI to supply a TOML file that overrides individual keys.

Keys and defaults
─────────────────
ebs_volume_grace_period_hours   int   24
    Volumes created within this many hours are skipped (provisioning grace).

ec2_stopped_days                int   30
    EC2 instances stopped for at least this many days are flagged.

iam_key_unused_days             int   90
    IAM access keys with no use (or never used) for this many days are flagged.

lb_no_traffic_days              int   14
    Load balancers with zero traffic for this many days are flagged.

nat_no_traffic_days             int   14
    NAT Gateways with ~zero traffic for this many days are flagged.

nat_min_bytes                   int   1_048_576   (1 MB)
    NAT Gateways whose total BytesOutToDestination over nat_no_traffic_days
    is below this threshold are flagged.

log_group_quiet_days            int   30
    Log groups with no ingestion for this many days are flagged (when they
    also have no retention policy and no metric filters).
"""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

try:
    import tomllib  # Python 3.11+
except ImportError:  # pragma: no cover
    import tomli as tomllib  # type: ignore[no-redef]

DEFAULT_CONFIG: dict[str, Any] = {
    "ebs_volume_grace_period_hours": 24,
    "ec2_stopped_days": 30,
    "iam_key_unused_days": 90,
    "lb_no_traffic_days": 14,
    "nat_no_traffic_days": 14,
    "nat_min_bytes": 1_048_576,  # 1 MB
    "log_group_quiet_days": 30,
}


def load_config(override_path: Path | None = None) -> dict[str, Any]:
    """
    Return a config dict starting from DEFAULT_CONFIG.
    If override_path is given, load it as TOML and merge over the defaults.
    Unknown keys in the TOML file are accepted (for forward-compat) but ignored.
    """
    cfg = copy.deepcopy(DEFAULT_CONFIG)
    if override_path is not None:
        raw = tomllib.loads(override_path.read_text())
        for key in DEFAULT_CONFIG:
            if key in raw:
                cfg[key] = raw[key]
    return cfg
