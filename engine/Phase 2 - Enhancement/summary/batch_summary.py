"""
batch_summary.py (Phase 2)

Builds batch-level summaries from per-chart summaries.
"""

from __future__ import annotations
from typing import Dict, Any, List


def build_batch_summary(
    *,
    per_chart_summaries: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Aggregate per-chart summaries into a batch summary.
    """
    total_charts = 0
    total_elements = 0

    for s in per_chart_summaries:
        if not isinstance(s, dict):
            continue
        total_charts += 1
        elements = s.get("elements")
        if isinstance(elements, list):
            total_elements += len(elements)

    return {
        "chart_count": total_charts,
        "element_count": total_elements,
        "charts": per_chart_summaries,
    }


__all__ = ["build_batch_summary"]