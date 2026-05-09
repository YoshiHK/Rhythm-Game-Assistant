"""
breakdown_formatter.py (Phase 2)

Formats chart breakdown explanations from cue-level signals.

This module produces short, explanatory text fragments
used later by the narrative layer.
"""

from __future__ import annotations
from typing import Dict, Any, List


def format_chart_breakdown(
    *,
    element: Dict[str, Any],
    cue_key: str = "cue_labels",
) -> str:
    """
    Format a chart breakdown string.

    Expected:
    - element may contain cue-level labels (optional)

    Fallback:
    - return a generic breakdown description
    """
    cues = element.get(cue_key)
    if not isinstance(cues, list) or not cues:
        return "The chart requires consistent execution across multiple sections."

    # Normalize cues
    clean: List[str] = []
    for c in cues:
        if isinstance(c, str):
            s = c.strip()
            if s:
                clean.append(s)

    if not clean:
        return "The chart combines multiple demanding patterns throughout."

    # Deterministic join
    if len(clean) == 1:
        return f"The chart emphasizes {clean[0]}."
    if len(clean) == 2:
        return f"The chart combines {clean[0]} and {clean[1]}."
    return f"The chart combines {', '.join(clean[:-1])}, and {clean[-1]}."


__all__ = ["format_chart_breakdown"]