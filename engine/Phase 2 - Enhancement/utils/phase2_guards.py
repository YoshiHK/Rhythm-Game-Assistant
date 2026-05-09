"""
phase2_guards.py (Phase 2)

Defensive guard helpers for Phase 2 execution.

Guards must never raise or block execution.
"""

from __future__ import annotations
from typing import Dict, Any, List


def guard_required_fields(
    *,
    payload: Dict[str, Any],
    required_fields: List[str],
) -> Dict[str, Any]:
    """
    Check presence of required fields in payload.

    Returns a report dict; never raises.
    """
    if not isinstance(payload, dict):
        return {
            "passed": False,
            "missing": required_fields,
        }

    missing = [f for f in required_fields if f not in payload]

    return {
        "passed": not missing,
        "missing": missing,
    }


__all__ = ["guard_required_fields"]