from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List


def validate_test_case_integrity(
    *,
    case_path: str | Path,
    integrity_spec: Dict[str, Any],
) -> Dict[str, Any]:

    errors: List[str] = []
    warnings: List[str] = []
    details: Dict[str, Any] = {}

    case_path = Path(case_path)

    # ------------------------------------------------------
    # Required files
    # ------------------------------------------------------
    for f in integrity_spec.get("required_files", []):
        if not (case_path / f).exists():
            errors.append(f"missing required file: {f}")

    # ------------------------------------------------------
    # Load input.json
    # ------------------------------------------------------
    input_path = case_path / "input.json"
    if not input_path.exists():
        errors.append("input.json missing")
        return {
            "validator": "test_case_integrity_validator",
            "passed": False,
            "errors": errors,
            "warnings": warnings,
            "details": {},
        }

    try:
        data = json.loads(input_path.read_text(encoding="utf-8"))
    except Exception:
        errors.append("invalid JSON in input.json")
        return {
            "validator": "test_case_integrity_validator",
            "passed": False,
            "errors": errors,
            "warnings": warnings,
            "details": {},
        }

    # ------------------------------------------------------
    # Input structure checks
    # ------------------------------------------------------
    req = integrity_spec.get("input_requirements", {})

    if req.get("require_event_category") and "event_category" not in data:
        errors.append("missing event_category")

    if req.get("require_payload"):
        if "payload" not in data or not isinstance(data["payload"], dict):
            errors.append("payload missing or not dict")

    payload = data.get("payload", {})

    for f in req.get("payload_required_fields", []):
        if f not in payload:
            errors.append(f"payload missing required field: {f}")

    # ------------------------------------------------------
    # Forbidden fields
    # ------------------------------------------------------
    forbidden = integrity_spec.get("file_integrity_rules", {}).get("no_top_level_game_fields", [])
    for f in forbidden:
        if f in data:
            errors.append(f"forbidden top-level field: {f}")

    # ------------------------------------------------------
    # Category rules
    # ------------------------------------------------------
    category = data.get("event_category")
    category_rules = integrity_spec.get("category_rules", {})

    if category in category_rules:
        details["category_expectation"] = category_rules[category]

    return {
        "validator": "test_case_integrity_validator",
        "passed": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "details": details,
    }