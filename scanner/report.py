"""
Graveyard Shift — report assembly and validation.

Assembles a Report from a list of Tombstones, validates against
schema/report.schema.json, and serialises to JSON.
"""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from pathlib import Path

import jsonschema

from scanner.models import Report, ReportSummary, Snapshot, Tombstone

_SCHEMA_PATH = Path(__file__).parent.parent / "schema" / "report.schema.json"
_SCHEMA: dict = json.loads(_SCHEMA_PATH.read_text())


def build_report(
    *,
    tombstones: list[Tombstone],
    snapshot: Snapshot,
    scan_duration: float,
    demo: bool,
) -> Report:
    """Assemble and return a validated Report."""
    summary = ReportSummary.from_tombstones(tombstones)
    report = Report(
        generated_at=datetime.now(tz=UTC),
        demo=demo,
        account_id=snapshot.account_id,
        regions_scanned=list(snapshot.regions),
        scan_duration_seconds=round(scan_duration, 3),
        tombstones=tombstones,
        summary=summary,
    )
    return report


def validate_report(report: Report) -> None:
    """
    Validate the report dict against the JSON Schema.
    Raises SystemExit(3) on failure.
    """
    report_dict = _report_to_dict(report)
    try:
        validator = jsonschema.Draft202012Validator(_SCHEMA)
        errors = list(validator.iter_errors(report_dict))
        if errors:
            for err in errors:
                print(f"Schema validation error: {err.message}", file=sys.stderr)
            sys.exit(3)
    except jsonschema.SchemaError as e:
        print(f"Internal schema error: {e}", file=sys.stderr)
        sys.exit(3)


def write_report(report: Report, out_path: Path) -> None:
    """Validate then write report JSON to disk."""
    validate_report(report)
    report_dict = _report_to_dict(report)
    out_path.write_text(json.dumps(report_dict, indent=2, default=_json_default))


def _report_to_dict(report: Report) -> dict:
    """Convert Report to a plain dict suitable for JSON serialisation.

    model_dump() keeps Python types (datetime, Decimal).
    We walk the dict and normalise:
      - Decimal  → float
      - datetime → ISO-8601 string
    so the result passes JSON Schema validation and json.dumps().
    """
    raw = report.model_dump()
    _normalise(raw)
    return raw


def _normalise(obj: object) -> None:
    """Recursively convert Decimal and datetime values in-place."""
    from datetime import datetime
    from decimal import Decimal as D

    if isinstance(obj, dict):
        for key, val in list(obj.items()):
            if isinstance(val, D):
                obj[key] = float(val)  # type: ignore[index]
            elif isinstance(val, datetime):
                obj[key] = val.isoformat()  # type: ignore[index]
            else:
                _normalise(val)
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            if isinstance(item, D):
                obj[i] = float(item)  # type: ignore[index]
            elif isinstance(item, datetime):
                obj[i] = item.isoformat()  # type: ignore[index]
            else:
                _normalise(item)


def _json_default(obj: object) -> object:
    from datetime import datetime
    from decimal import Decimal as D

    if isinstance(obj, D):
        return float(obj)
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serialisable")
