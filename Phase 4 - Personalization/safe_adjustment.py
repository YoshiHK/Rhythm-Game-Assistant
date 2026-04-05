
#!/usr/bin/env python3
"""
safe_adjustment.py

Phase 4 Safe Adjustment Interface implementation stub.
Applies non‑destructive personalization adjustments.
"""
from typing import List, Dict, Any


def apply_safe_adjustments(
    elements_skeleton: List[Dict[str, Any]],
    adjustment_directives: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Apply Phase‑4 safe adjustments.

    Returns a presentation‑layer view without mutating inputs.
    """

    # Shallow copy for safety
    elements_view = list(elements_skeleton)
    applied = {}

    # Element ordering
    order = adjustment_directives.get('element_ordering')
    if isinstance(order, list):
        id_map = {el.get('element_id'): el for el in elements_view}
        reordered = [id_map[eid] for eid in order if eid in id_map]
        if len(reordered) == len(elements_view):
            elements_view = reordered
            applied['element_ordering'] = order

    # Scalar weights (presentation only)
    weights = adjustment_directives.get('ranking_weights')
    if isinstance(weights, dict):
        applied['ranking_weights'] = weights

    return {
        'elements_view': elements_view,
        'applied_adjustments': applied,
    }


__all__ = ['apply_safe_adjustments']
