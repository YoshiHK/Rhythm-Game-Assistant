from __future__ import annotations
from typing import Any, Dict, List

from inference.model_gateway import run_model_inference as _run_model_inference

_ALLOWED_DIRECTIVES = {
    "element_ordering",
    "ranking_weights",
    "narrative_template_id",
    "variant_id",
}


def run_model_inference(
    *,
    decision: Dict[str, Any],
    canonical_payload: Dict[str, Any],
    elements_skeleton: List[Dict[str, Any]],
    include_experimental_variants: bool,
) -> Dict[str, Any]:
    """Runtime adapter for Phase 4 Model Inference."""
    base_directives = decision.get("adjustment_directives") or {}

    if decision.get("decision_source") == "rule":
        return {
            "adjustment_directives": {
                k: v for k, v in base_directives.items()
                if k in _ALLOWED_DIRECTIVES
            }
        }

    difficulty = decision.get("difficulty")
    locale = decision.get("locale")
    canonical_row = decision.get("canonical_row") or {}

    inferred = _run_model_inference(
        canonical_payload=canonical_payload,
        canonical_row=canonical_row,
        elements_skeleton=elements_skeleton,
        difficulty=difficulty,
        locale=locale,
        include_experimental_variants=include_experimental_variants,
    )

    merged: Dict[str, Any] = {}
    for k in _ALLOWED_DIRECTIVES:
        if k in base_directives:
            merged[k] = base_directives[k]
        elif k in inferred:
            merged[k] = inferred[k]

    return {"adjustment_directives": merged}