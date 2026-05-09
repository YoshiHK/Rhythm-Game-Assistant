"""
per_chart_summary.py (Phase 2)

Builds canonical per-chart summary objects.
"""

from __future__ import annotations
from typing import Dict, Any, List

from .dominance_score import compute_dominance_score


def build_per_chart_summary(
    *,
    selected_elements: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Build a per-chart summary from selected analysed elements.
    """
    elements_out: List[Dict[str, Any]] = []

    for e in selected_elements:
        if not isinstance(e, dict):
            continue

        score = e.get("score", 0.0)
        coverage = e.get("section_coverage", 0.0)

        dominant_score = compute_dominance_score(
            score=score,
            section_coverage=coverage,
        )

        elements_out.append({
            **e,
            "dominant_score": dominant_score,
        })

    # Stable ordering: by dominant_score desc, then name
    elements_out.sort(
        key=lambda x: (
            -float(x.get("dominant_score", 0.0)),
            str(x.get("name") or x.get("element_name") or ""),
        )
    )

    return {
        "elements": elements_out,
    }


__all__ = ["build_per_chart_summary"]