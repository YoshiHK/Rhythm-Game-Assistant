"""
non_destructive_checks.py (Phase 2)

Checks that Phase 1 outputs are not destructively modified
by Phase 2 enhancements.
"""

from __future__ import annotations
from typing import Any, Dict


def check_non_destructive(
    *,
    phase1_output: Dict[str, Any],
    phase2_output: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Verify that Phase 1 keys are preserved in Phase 2 output.

    Returns a report dict; never raises.
    """
    if not isinstance(phase1_output, dict) or not isinstance(phase2_output, dict):
        return {
            "check": "non_destructive",
            "passed": False,
            "details": "Invalid inputs for non-destructive check",
        }

    removed = [k for k in phase1_output.keys() if k not in phase2_output]

    return {
        "check": "non_destructive",
        "passed": not removed,
        "details": None if not removed else f"Removed keys: {removed}",
    }


__all__ = ["check_non_destructive"]