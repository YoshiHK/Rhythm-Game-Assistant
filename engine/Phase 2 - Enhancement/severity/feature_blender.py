"""
feature_blender.py (Phase 2)

Optional feature-based score refinement.

This module blends chart-level scalar features derived
from SectionMetrics into element scores.

It must remain:
- deterministic
- bounded
- dominance-safe
"""

from __future__ import annotations
from typing import List, Dict, Any


def blend_features_into_score(
    *,
    base_score: float,
    sections: List[Dict[str, Any]],
    weight: float = 0.0,
) -> float:
    """
    Blend chart-level features into base score.

    Default behavior:
    - no blending (weight = 0.0)

    Future extensions may compute scalars from sections
    and adjust score conservatively.
    """
    try:
        score = float(base_score)
    except Exception:
        score = 0.0

    # Currently no-op by design
    score = score + weight * 0.0
    return max(0.0, min(1.0, score))


__all__ = ["blend_features_into_score"]