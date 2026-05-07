#!/usr/bin/env python3
from __future__ import annotations

"""
Phase 4 Model Inference Layer (bounded, advisory)

Provides three bounded components:
- RankingModel: suggests per-element weights and/or ordering (presentation-only)
- TemplateSelector: suggests narrative template ID (from a safe registry)
- BanditPolicy: chooses a variant for constrained exploration (safe-only)

Hard constraints:
- No IO by default (registries/configs are provided by caller)
- No online learning
- No free-form text generation
- Does not mutate inputs
- Must not modify Phase 1–3 semantics
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from .inference_types import PlayerContext, InferenceInputs, InferenceOutputs


class RankingModel:
    """
    Presentation-only ranking model.
    Default implementation is a no-op (deterministic).
    """

    def suggest_weights(self, inputs: InferenceInputs) -> Dict[str, float]:
        return {}

    def suggest_ordering(self, inputs: InferenceInputs) -> Optional[List[str]]:
        return None


class TemplateSelector:
    """
    Selects a narrative template ID from an allow-list registry.
    Default behavior: choose the first allowed template for the given difficulty.
    """

    def select(self, *, difficulty: str, template_registry: Dict[str, List[str]]) -> Optional[str]:
        ids = template_registry.get(difficulty) or []
        return str(ids[0]) if ids else None


@dataclass
class BanditPolicy:
    """
    Constrained exploration over variants.

    Deterministic by default:
    - chooses the first allowed variant
    Randomness is disabled unless explicitly enabled (not recommended in Phase 4 runtime).
    """

    policy: str = "first"
    epsilon: float = 0.0
    enable_randomness: bool = False

    def choose(self, *, template_id: str, variant_registry: Dict[str, List[str]]) -> Optional[str]:
        variants = variant_registry.get(template_id) or []
        if not variants:
            return None
        return str(variants[0])


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
    Run bounded Phase 4 model inference (advisory only).

    Determinism:
    - Outside personalized mode -> returns empty outputs
    - Default components are deterministic (no randomness)
    """

    template_registry = template_registry or {}
    variant_registry = variant_registry or {}
    ranking_model = ranking_model or RankingModel()
    template_selector = template_selector or TemplateSelector()

    if inputs.engine_mode != "personalized":
        return InferenceOutputs(
            ranking_weights={},
            element_ordering=None,
            narrative_template_id=None,
            variant_id=None,
            bandit_meta=None,
        )

    weights = ranking_model.suggest_weights(inputs) or {}
    ordering = ranking_model.suggest_ordering(inputs)

    template_id = template_selector.select(
        difficulty=inputs.difficulty,
        template_registry=template_registry,
    )

    chosen_variant: Optional[str] = None
    bandit_meta: Optional[Dict[str, Any]] = None

    if template_id and bandit_policy is not None:
        chosen_variant = bandit_policy.choose(
            template_id=template_id,
            variant_registry=variant_registry,
        )
        bandit_meta = {
            "policy": bandit_policy.policy,
            "epsilon": bandit_policy.epsilon,
            "deterministic": not bandit_policy.enable_randomness,
        }

    return InferenceOutputs(
        ranking_weights={str(k): float(v) for k, v in weights.items() if k},
        element_ordering=[str(x) for x in ordering] if isinstance(ordering, list) else None,
        narrative_template_id=str(template_id) if template_id else None,
        variant_id=str(chosen_variant) if chosen_variant else None,
        bandit_meta=bandit_meta,
    )


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

    Output shape:
      {
        "ranking_weights": {...},
        "element_ordering": [...],
        "narrative_template_id": "...",
        "variant_id": "...",
        "bandit_meta": {...}
      }

    NOTE:
    - include_experimental_variants is accepted for contract compatibility,
      but this module remains deterministic by default.
    """

    player = PlayerContext(player_id_hash=None, locale=locale, cohort=None)
    inputs = InferenceInputs(
        engine_mode="personalized",
        difficulty=difficulty,
        elements_skeleton=list(elements_skeleton),
        canonical_payload=dict(canonical_payload),
        canonical_row=dict(canonical_row),
        player=player,
    )

    outputs = run_phase4_model_inference(
        inputs,
        template_registry=template_registry,
        variant_registry=variant_registry,
        ranking_model=None,
        template_selector=None,
        bandit_policy=None,  # keep deterministic default: no bandit unless injected by caller
    )

    directives: Dict[str, Any] = {}
    if outputs.ranking_weights:
        directives["ranking_weights"] = outputs.ranking_weights
    if outputs.element_ordering:
        directives["element_ordering"] = outputs.element_ordering
    if outputs.narrative_template_id:
        directives["narrative_template_id"] = outputs.narrative_template_id
    if outputs.variant_id:
        directives["variant_id"] = outputs.variant_id

    # bandit metadata is record-only
    if outputs.bandit_meta:
        directives["bandit_meta"] = outputs.bandit_meta

    return directives


__all__ = [
    "PlayerContext",
    "InferenceInputs",
    "InferenceOutputs",
    "RankingModel",
    "TemplateSelector",
    "BanditPolicy",
    "run_phase4_model_inference",
    "run_model_inference",
]