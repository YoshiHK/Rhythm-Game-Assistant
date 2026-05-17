from __future__ import annotations

from typing import Any, Dict, List

from .adjustment_constraints import validate_directives


def apply_safe_adjustment(
    *,
    elements_skeleton: List[Dict[str, Any]],
    adjustment_directives: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Implements the Phase 4 Safe Adjustment Interface.

    Returns a presentation-layer view without mutating inputs.
    Invalid directives -> no-op fallback.
    """

    elements_view = list(elements_skeleton)
    applied: Dict[str, Any] = {}

    if not adjustment_directives:
        return {"elements_view": elements_view, "applied_adjustments": applied}

    if not validate_directives(adjustment_directives):
        return {"elements_view": elements_view, "applied_adjustments": applied}

    # Element ordering (only if complete)
    order = adjustment_directives.get("element_ordering")
    if isinstance(order, list):
        id_map = {}
        for el in elements_view:
            eid = el.get("element_id") or el.get("id")
            if eid is not None:
                id_map[str(eid)] = el

        reordered = [id_map[str(eid)] for eid in order if str(eid) in id_map]

        if len(reordered) == len(elements_view):
            elements_view = reordered
            applied["element_ordering"] = [str(x) for x in order]

    # Scalar weights (presentation only)
    weights = adjustment_directives.get("ranking_weights")
    if isinstance(weights, dict):
        applied["ranking_weights"] = {str(k): float(v) for k, v in weights.items() if k}

    # template/variant are record-only hints (used by narrative bridge)
    if isinstance(adjustment_directives.get("narrative_template_id"), str):
        applied["narrative_template_id"] = adjustment_directives["narrative_template_id"]

    if isinstance(adjustment_directives.get("variant_id"), str):
        applied["variant_id"] = adjustment_directives["variant_id"]

    return {"elements_view": elements_view, "applied_adjustments": applied}
