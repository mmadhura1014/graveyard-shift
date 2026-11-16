"""
M1 integration tests: seed report validation and cross-detector checks.
"""

from __future__ import annotations

import json
from pathlib import Path

import jsonschema

SCHEMA_PATH = Path("schema/report.schema.json")
SEED_REPORT = Path("seed/report.json")


def test_schema_is_valid_draft_2020_12():
    schema = json.loads(SCHEMA_PATH.read_text())
    jsonschema.Draft202012Validator.check_schema(schema)


def test_seed_report_validates_against_schema():
    schema = json.loads(SCHEMA_PATH.read_text())
    report = json.loads(SEED_REPORT.read_text())
    jsonschema.validate(report, schema)


def test_seed_report_is_demo():
    report = json.loads(SEED_REPORT.read_text())
    assert report["demo"] is True


def test_seed_report_account_id_is_fake():
    report = json.loads(SEED_REPORT.read_text())
    assert report["account_id"] == "111122223333"
    for t in report["tombstones"]:
        assert t["account_id"] == "111122223333"


def test_seed_report_has_tombstones():
    report = json.loads(SEED_REPORT.read_text())
    assert report["summary"]["total_tombstones"] > 0
    assert len(report["tombstones"]) == report["summary"]["total_tombstones"]


def test_seed_report_all_costs_non_negative():
    report = json.loads(SEED_REPORT.read_text())
    for t in report["tombstones"]:
        assert t["estimated_monthly_cost"] >= 0, f"Tombstone {t['resource_id']} has negative cost"


def test_seed_report_summary_cost_equals_sum():
    report = json.loads(SEED_REPORT.read_text())
    total = sum(t["estimated_monthly_cost"] for t in report["tombstones"])
    assert abs(report["summary"]["estimated_monthly_cost"] - total) < 0.01


def test_seed_report_severity_counts_sum_to_total():
    report = json.loads(SEED_REPORT.read_text())
    sev = report["summary"]["by_severity"]
    total = sev["harmless"] + sev["wasteful"] + sev["risky"]
    assert total == report["summary"]["total_tombstones"]


def test_seed_report_no_real_account_ids_in_text():
    import re

    text = SEED_REPORT.read_text()
    # Find 12-digit strings that are NOT the fake account ID
    matches = re.findall(r"\b(?!111122223333)\d{12}\b", text)
    assert matches == [], f"Possible real account IDs found: {matches}"


def test_seed_report_all_exorcism_cli_contain_resource_id():
    report = json.loads(SEED_REPORT.read_text())
    for t in report["tombstones"]:
        assert t["resource_id"] in t["exorcism_cli"], (
            f"exorcism_cli for {t['resource_id']} does not contain the resource_id"
        )


def test_seed_report_zombie_resources_are_flagged(seed_snapshot, default_config):
    """Key zombie resources in the seed snapshot should all appear."""
    from scanner.detectors import ALL_DETECTORS

    tombstones = []
    for detector in ALL_DETECTORS:
        tombstones.extend(detector(seed_snapshot, default_config))

    ids = {t.resource_id for t in tombstones}
    # EBS volumes: vol-0dead000000000001 and vol-0dead000000000002 (not 3 — within grace)
    assert "vol-0dead000000000001" in ids
    assert "vol-0dead000000000002" in ids
    # EBS volume from eu-west-1
    assert "vol-0dead000000000004" in ids
    # Orphaned snapshots
    assert "snap-0dead00000000001" in ids
    assert "snap-0dead00000000002" in ids
    # Unassociated EIPs
    assert "eipalloc-0dead0000000001" in ids
    assert "eipalloc-0dead0000000002" in ids


def test_seed_report_clean_resources_not_flagged(seed_snapshot, default_config):
    """The live/clean resources in the seed snapshot should NOT be flagged."""
    from scanner.detectors import ALL_DETECTORS

    tombstones = []
    for detector in ALL_DETECTORS:
        tombstones.extend(detector(seed_snapshot, default_config))

    ids = {t.resource_id for t in tombstones}
    # In-use volume
    assert "vol-0live000000000001" not in ids
    # Snapshot whose source volume exists
    assert "snap-0live00000000001" not in ids
    # AWS-owned snapshot
    assert "snap-0aws000000000001" not in ids
    # Associated EIP
    assert "eipalloc-0live0000000001" not in ids
