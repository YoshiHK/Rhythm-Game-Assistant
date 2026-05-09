"""
cause_resolver.py (Phase 2)

Resolves dominant difficulty causes for an analysed element
based on taxonomy categories and cue import Dict, Any, List, Tuplebased on taxonomy categories and cue signals.


def resolve_difficulty_causes(
    *,
    element: Dict[str, Any],
    taxonomy_key: str = "taxonomy_categories",
) -> Tuple[str, str]:
    """
    Resolve primary and secondary difficulty causes.

    Expected input:
    - element may contain taxonomy category signals (optional)

    Fallback behavior:
    - return generic causes when signals are missing
    """
    cats = element.get(taxonomy_key)
    if not isinstance(cats, list) or not cats:
        return "mechanical consistency", "pattern recognition"

    # Normalize and count
    counts: Dict[str, int] = {}
    for c in cats:
        if isinstance(c, str):
            k = c.strip().lower()
            if k:
                counts[k] = counts.get(k, 0) + 1

    if not counts:
        return "mechanical consistency", "pattern recognition"

    # Sort by frequency, then name for stability
    ranked = sorted(counts.items(), key=lambda x: (-x[1], x[0]))

    primary = ranked[0][0]
    secondary = ranked[1][0] if len(ranked) > 1 else primary

    return primary, secondary


__all__ = ["resolve_difficulty_causes"]

This module is deterministic and conservative.
"""

from __future__ import annotations
