"""
determinism_checks.py (Phase 2)

Checks that Phase 2 outputs are deterministic.
"""

from __future__ import annotations
from typing import Any, Dict


def check_determinism(
    *,
    first_output: Dict[str, Any],
    second_output: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Compare two outputs produced from identical inputs.

    Returns a report dict; never raises.
    """
    identical = first_output == second_output

    return {
        "check": "determinism",
        "passed": identical,
        "details": None if identical else "Outputs differ for identical inputs",
    }


__all__ = ["check_determinism"]
``