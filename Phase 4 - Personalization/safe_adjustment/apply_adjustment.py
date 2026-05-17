from __future__ import annotations

"""
Phase 4 Safe Adjustment — apply_adjustment

Contract expectations (CI):
- Canonical entrypoint: apply_safe_adjustment (singular)
- Backward-compatible alias: apply_safe_adjustments (plural)
- Presentation-only: MUST NOT mutate input elements
"""

from typing import Any, Dict, List
from .adjustment_constraints import validate_directives


def apply_safe_adjustment(
    *,
    elements_skeleton: List[Dict[str, Any]],
    adjustment_directives: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Apply presentation-only adjustment directives.

    Returns:
      {
        "elements_view": <list>,
        "applied_adjustments": <dict>
      }

    Behavior:
    - empty/invalid directives -> no-op
    - element_ordering -> applied only when it's a complete permutation
    - ranking_weights/template/variant -> record-only hints
    """
    elements_view = list(elements_skeleton)  # do not mutate input
    applied: Dict[str, Any] = {}

    if not adjustment_directives:
        return {"elements_view": elements_view, "applied_adjustments": applied}

    if not validate_directives(adjustment_directives):
        return {"elements_view": elements_view, "applied_adjustments": applied}

    # Element ordering (only if complete permutation)
    order = adjustment_directives.get("element_ordering")
    if isinstance(order, list):
        id_map: Dict[str, Dict[str, Any]] = {}
        for el in elements_view:
            eid = el.get("element_id") or el.get("id")
            if eid is not None:
                id_map[str(eid)] = el

        reordered = [id_map[str(eid)] for eid in order if str(eid) in id_map]
        if len(reordered) == len(elements_view):
            elements_view = reordered
            applied["element_ordering"] = [str(x) for x in order]

    # ranking_weights (record-only)
    weights = adjustment_directives.get("ranking_weights")
    if isinstance(weights, dict):
        applied["ranking_weights"] = {
            str(k): float(v) for k, v in weights.items() if isinstance(k, str) and k
        }

    # narrative_template_id / variant_id (record-only)
    tpl = adjustment_directives.get("narrative_template_id")
    if isinstance(tpl, str):
        applied["narrative_template_id"] = tpl

    var = adjustment_directives.get("variant_id")
    if isinstance(var, str):
        applied["variant_id"] = var

    return {"elements_view": elements_view, "applied_adjustments": applied}


def apply_safe_adjustments(
    *,
    elements_skeleton: List[Dict[str, Any]],
    adjustment_directives: Dict[str, Any],
) -> Dict[str, Any]:
    """Backward-compatible alias."""
    return apply_safe_adjustment(
        elements_skeleton=elements_skeleton,
        adjustment_directives=adjustment_directives,
    )
