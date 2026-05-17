#!/usr/bin/env python3
from __future__ import annotations

"""
Phase 4 Model Inference Layer (bounded, advisory)

Hard constraints:
- No I/O by default
- No online learning
- No free-form text generation
- Deterministic for identical inputs
- Presentation-only (returns adjustment directives only)
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

# Keep these imports if you use the typed contracts; safe even if unused
try:
    from .inference_types import PlayerContext, InferenceInputs, InferenceOutputs
except Exception:
    PlayerContext = Any  # type: ignore
    InferenceInputs = Any  # type: ignore
    InferenceOutputs = Any  # type: ignore


class RankingModel:
    """Presentation-only ranking model. Default = no-op."""
    def infer(self, elements_skeleton: List[Dict[str, Any]]) -> Dict[str, float]:
        return {}


class TemplateSelector:
    """Selects a narrative template id from allow-list. Default = no-op."""
    def select(self, template_registry: Optional[Dict[str, List[str]]], difficulty: str) -> Optional[str]:
        if not template_registry:
            return None
        # pick first available deterministically
        for _, ids in template_registry.items():
            if ids:
                return str(ids[0])
        return None


@dataclass
class BanditPolicy:
    """Constrained exploration over variants. Default = no-op."""
    def choose(self, variant_registry: Optional[Dict[str, List[str]]], difficulty: str) -> Optional[str]:
        if not variant_registry:
            return None
        # pick first available deterministically
        for _, ids in variant_registry.items():
            if ids:
                return str(ids[0])
        return None


def run_phase4_model_inference(
    inputs: InferenceInputs,
    *,
    template_registry: Optional[Dict[str, List[str]]] = None,
    variant_registry: Optional[Dict[str, List[str]]] = None,
    ranking_model: Optional[RankingModel] = None,
    template_selector: Optional[TemplateSelector] = None,
    bandit_policy: Optional[BanditPolicy] = None,
) -> InferenceOutputs:
    """
    Deterministic bounded inference (advisory).
    Returns only presentation directives.
    """
    # Default components
    ranking_model = ranking_model or RankingModel()
    template_selector = template_selector or TemplateSelector()
    bandit_policy = bandit_policy or BanditPolicy()

    elements = getattr(inputs, "elements_skeleton", None) or []
    difficulty = getattr(inputs, "difficulty", None) or "unknown"

    out: Dict[str, Any] = {}

    # ranking_weights (presentation only)
    weights = ranking_model.infer(elements)
    if weights:
        out["ranking_weights"] = weights

    # narrative_template_id / variant_id (presentation hints)
    tpl = template_selector.select(template_registry, str(difficulty))
    if tpl:
        out["narrative_template_id"] = tpl

    var = bandit_policy.choose(variant_registry, str(difficulty))
    if var:
        out["variant_id"] = var

    # element_ordering not emitted by default (keep no-op)
    return out  # type: ignore


def run_model_inference(
    *,
    canonical_payload: Dict[str, Any],
    canonical_row: Dict[str, Any],
    elements_skeleton: List[Dict[str, Any]],
    difficulty: str,
    locale: Optional[str],
    include_experimental_variants: bool,
    template_registry: Optional[Dict[str, List[str]]] = None,
    variant_registry: Optional[Dict[str, List[str]]] = None,
) -> Dict[str, Any]:
    """
    Convenience wrapper returning Phase-4 adjustment directives dict.
    Deterministic, bounded, presentation-only.
    """
    # Build a minimal inputs-like object (avoids coupling to dataclass)
    class _Inputs:
        def __init__(self):
            self.canonical_payload = canonical_payload
            self.canonical_row = canonical_row
            self.elements_skeleton = elements_skeleton
            self.difficulty = difficulty
            self.locale = locale
            self.include_experimental_variants = include_experimental_variants

    directives = run_phase4_model_inference(
        _Inputs(),  # type: ignore
        template_registry=template_registry,
        variant_registry=variant_registry,
    )

    # Ensure only allowed keys appear
    allowed = {"element_ordering", "ranking_weights", "narrative_template_id", "variant_id"}
    return {k: v for k, v in dict(directives).items() if k in allowed}


# ✅ Backward-compatible alias (fixes your failing import)
run_inference = run_model_inference


__all__ = [
    "PlayerContext",
    "InferenceInputs",
    "InferenceOutputs",
    "RankingModel",
    "TemplateSelector",
    "BanditPolicy",
    "run_phase4_model_inference",
    "run_model_inference",
    "run_inference",
]