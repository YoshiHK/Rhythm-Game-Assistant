"""
calibration_bridge.py (Phase 2)

Optional calibration layer for severity and score.

This module:
- preserves severity labels by default
- allows midpoint or config-based score adjustments
"""

from __future__ import annotations
from typing import Tuple


def apply_severity_calibration(
    *,
    severity: str,
    score: float,
) -> Tuple[str, float]:
    """
    Apply calibration to severity and score.

    Default behavior:
    - severity label unchanged
    - score passed through unchanged

    Hook point for:
    - midpoint overrides
    - external calibration configs (Phase 2.1+)
    """
    # Defensive bounds
    try:
        score = float(score)
    except Exception:
        score = 0.0

    score = max(0.0, min(1.0, score))
    return severity, score


__all__ = ["apply_severity_calibration"]