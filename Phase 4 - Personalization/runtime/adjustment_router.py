from __future__ import annotations
from typing import Any, Dict, List

from safe_adjustment.apply_adjustment import apply_safe_adjustment


def apply_adjustments(
    *,
    base_elements: List[Dict[str, Any]],
    base_narrative: Any,
    adjustment_directives: Dict[str, Any],
    provenance: Dict[str, Any],
) -> Dict[str, Any]:
    """Runtime adapter for Phase 4 Safe Adjustment."""
    result = apply_safe_adjustment(
        elements_skeleton=base_elements,
        adjustment_directives=adjustment_directives,
    )

    provenance_out = dict(provenance)
    provenance_out["safe_adjustment_applied"] = bool(result.get("applied_adjustments"))

    return {
        "elements_view": result["elements_view"],
        "applied_adjustments": result["applied_adjustments"],
        "provenance": provenance_out,
    }