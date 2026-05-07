from __future__ import annotations

"""
debug_helpers.py

Phase 4 — Debug and inspection helpers.

Pure helper functions intended for:
- debug logs
- test assertions
- CI inspection output

This module must remain side-effect free.
"""

from typing import Any, Dict, Iterable


def summarize_adjustments(adjustments: Dict[str, Any]) -> Dict[str, Any]:
    """
    Produce a compact, human-readable summary of adjustment directives.

    Useful for debug logs and explainability output.
    """

    summary: Dict[str, Any] = {}

    if not isinstance(adjustments, dict):
        return summary

    if "element_ordering" in adjustments:
        order = adjustments.get("element_ordering")
        if isinstance(order, list):
            summary["element_count"] = len(order)

    if "ranking_weights" in adjustments:
        weights = adjustments.get("ranking_weights")
        if isinstance(weights, dict):
            summary["weighted_elements"] = len(weights)

    if "narrative_template_id" in adjustments:
        summary["template"] = adjustments.get("narrative_template_id")

    if "variant_id" in adjustments:
        summary["variant"] = adjustments.get("variant_id")

    return summary


def safe_repr(value: Any, *, max_len: int = 200) -> str:
    """
    Return a safe, truncated string representation for debug output.
    """

    try:
        s = repr(value)
    except Exception:
        return "<unreprable>"

    if len(s) <= max_len:
        return s

    return s[: max_len - 3] + "..."


__all__ = [
    "summarize_adjustments",
    "safe_repr",
]