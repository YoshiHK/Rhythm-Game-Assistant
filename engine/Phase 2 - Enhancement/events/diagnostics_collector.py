"""
diagnostics_collector.py (Phase 2)

Collects non-invasive diagnostics snapshots for Phase 2 runs.
"""

from __future__ import annotations

from typing import Any, Dict, List


def collect_diagnostics(
    *,
    stage: str,
    analysed_elements: List[Dict[str, Any]] | None = None,
) -> Dict[str, Any]:
    """
    Collect diagnostics for a given stage.

    Diagnostics are intended for QA and observability only.
    """
    analysed_elements = analysed_elements or []

    return {
        "stage": stage,
        "element_count": len(analysed_elements),
        "has_chart_defining": any(
            bool(e.get("is_chart_defining"))
            for e in analysed_elements
            if isinstance(e, dict)
        ),
    }


__all__ = ["collect_diagnostics"]