"""
dominance_score.py (Phase 2)

Defines the canonical dominance score used in summaries.

Dominance score:
    dominant_score = score * section_coverage
"""

from __future__ import annotations


def compute_dominance_score(*, score: float, section_coverage: float) -> float:
    """
    Compute dominance score in a bounded, deterministic way.
    """
    try:
        s = float(score)
    except Exception:
        s = 0.0

    try:
        c = float(section_coverage)
    except Exception:
        c = 0.0

    s = max(0.0, min(1.0, s))
    c = max(0.0, min(1.0, c))

    return s * c


__all__ = ["compute_dominance_score"]