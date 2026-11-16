"""
Graveyard Shift — cost estimation from bundled pricing table.

All cost figures are ESTIMATES derived from AWS public pricing pages.
The pricing table is bundled at scanner/pricing.json with a last_updated date.
Costs are never presented as measured or exact values.
"""

from __future__ import annotations

import json
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path
from typing import Any

_PRICING_FILE = Path(__file__).parent / "pricing.json"
_PRICING: dict[str, Any] = json.loads(_PRICING_FILE.read_text())

HOURS_PER_MONTH = Decimal("730")  # 365 * 24 / 12


def _multiplier(region: str) -> Decimal:
    multipliers: dict[str, float] = _PRICING.get("region_multipliers", {})
    return Decimal(str(multipliers.get(region, 1.0)))


def _price(key: str) -> Decimal:
    prices: dict[str, float] = _PRICING["prices"]
    if key not in prices:
        raise KeyError(f"Unknown pricing key: {key!r}")
    return Decimal(str(prices[key]))


def _round(d: Decimal) -> Decimal:
    return d.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def get_monthly_cost(resource_type: str, metadata: dict[str, Any], region: str) -> Decimal:
    """
    Return an estimated monthly USD cost for a zombie resource.
    Returns Decimal("0") for resource types with no direct cost (e.g. IAM keys, security groups).
    All returned values are >= 0.
    """
    mult = _multiplier(region)

    if resource_type == "EC2::Volume":
        volume_type = metadata.get("volume_type", "gp2").lower()
        size_gib = Decimal(str(metadata.get("size_gib", 0)))
        price_key = f"ebs_{volume_type}_per_gb_month"
        # Fall back to gp2 if the type isn't in the table
        if price_key not in _PRICING["prices"]:
            price_key = "ebs_gp2_per_gb_month"
        return _round(_price(price_key) * size_gib * mult)

    if resource_type == "EC2::Snapshot":
        size_gib = Decimal(str(metadata.get("size_gib", 0)))
        return _round(_price("snapshot_per_gb_month") * size_gib * mult)

    if resource_type == "EC2::EIP":
        return _round(_price("eip_unassociated_per_hr") * HOURS_PER_MONTH * mult)

    if resource_type == "ELB::LoadBalancer":
        lb_type = metadata.get("lb_type", "ALB").upper()
        price_key = "alb_per_hr" if lb_type == "ALB" else "nlb_per_hr"
        return _round(_price(price_key) * HOURS_PER_MONTH * mult)

    if resource_type == "EC2::NatGateway":
        # Hourly cost only (data cost can't be estimated for idle GWs)
        return _round(_price("nat_per_hr") * HOURS_PER_MONTH * mult)

    if resource_type == "EC2::Instance":
        # Stopped instances accrue EBS costs only; use attached EBS size
        ebs_size_gib = Decimal(str(metadata.get("ebs_size_gib", 0)))
        # Assume gp2 as a conservative default (cheapest common type)
        return _round(_price("ebs_gp2_per_gb_month") * ebs_size_gib * mult)

    if resource_type == "IAM::AccessKey":
        # No direct monetary cost; return 0 (security risk, not financial)
        return Decimal("0")

    if resource_type == "EC2::SecurityGroup":
        # No direct cost
        return Decimal("0")

    if resource_type == "CWLogs::LogGroup":
        stored_gb = Decimal(str(metadata.get("stored_bytes", 0))) / Decimal("1073741824")
        return _round(_price("cw_logs_per_gb_month") * stored_gb * mult)

    # Unknown type — return 0 rather than raising
    return Decimal("0")


def pricing_last_updated() -> str:
    return _PRICING.get("last_updated", "unknown")
