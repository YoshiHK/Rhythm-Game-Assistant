"""
schema_alignment_checks.py (Phase 2)

Validates alignment with Phase 2 schemas.

Note:
- This module performs shallow structural checks only.
- Full JSON Schema validation may be performed externally.
"""

from __future__ import annotations
from typing import Any, Dict, List


def _has_keys(obj: Dict[str, Any], keys: List[str]) -> bool:
    return all(k in obj for k in keys)


def check_schema_alignment(
    *,
    output: Dict[str, Any],
    required_keys: List[str],
) -> Dict[str, Any]:
    """
    Check that required keys are present in the output.

    Returns a report dict; never raises.
    """
    if not isinstance(output, dict):
        return {
            "check": "schema_alignment",
            "passed": False,
            "details": "Output is not a dict",
        }

    missing = [k for k in required_keys if k not in output]

    return {
        "check": "schema_alignment",
        "passed": not missing,
        "details": None if not missing else f"Missing keys: {missing}",
    }


__all__ = ["check_schema_alignment"]