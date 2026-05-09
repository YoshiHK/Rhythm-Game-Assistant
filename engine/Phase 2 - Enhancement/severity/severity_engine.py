"""
severity_engine.py (Phase 2)

Track A coordinator for severity, score, and coverage inference.

This module:
- builds on Phase 1 baseline inference
- applies optional Phase 2 enhancements
- emits analysed elements compliant with Phase 2 schemas

No selection, guidance, or personalization logic is allowed here.
"""

from __future__ import annotations
from typing import Dict, Any, List

from .coverage_calculator import compute_section_coverage
from .calibration_bridge import apply_severity_calibration
from .feature_blender import blend_features_into_score


def run_severity_analysis(
    *,
    elements: List[Dict[str, Any]],
    sections: List[Dict[str, Any]],
    enable_calibration: bool = True,
    enable_feature_blending: bool = False,
) -> List[Dict[str, Any]]:
    """
    Run Phase 2 severity analysis (Track A).

    Input:
    - elements: baseline analysed elements (Phase 1 semantics)
    - sections: SectionMetrics list

    Output:
    - analysed elements with refined score and section_coverage
    """
    out: List[Dict[str, Any]] = []

    for elem in elements:
        if not isinstance(elem, dict):
            continue

        severity = elem.get("severity")
        score = elem.get("score")
        name = elem.get("name")

        # Compute coverage (pure function)
        coverage = compute_section_coverage(
            element_name=name,
            sections=sections,
        )

        # Optional calibration (label-preserving by default)
        if enable_calibration:
            severity, score = apply_severity_calibration(
                severity=severity,
                score=score,
            )

        # Optional feature blending
        if enable_feature_blending:
            score = blend_features_into_score(
                base_score=score,
                sections=sections,
            )

        out.append({
            **elem,
            "severity": severity,
            "score": score,
            "section_coverage": coverage,
        })

    return out


__all__ = ["run_severity_analysis"]