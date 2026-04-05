
#!/usr/bin/env python3
"""phase4_model_inference.py

Phase 4 Model Inference Layer.

Provides three bounded components:
- RankingModel: suggests per-element weights and/or ordering (presentation-only)
- TemplateSelector: suggests narrative template ID (from a safe registry)
- BanditPolicy: chooses a variant for constrained exploration (safe-only)

This module is intentionally conservative:
- No IO by default (callers can provide registries/configs)
- No online learning
- No free-form text generation
- Does not mutate inputs
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence, Tuple
import random


# ----------------------------
# Data contracts (lightweight)
# ----------------------------

@dataclass(frozen=True)
class PlayerContext:
    player_id_hash: Optional[str] = None
    locale: Optional[str] = None
    cohort: Optional[str] = None


@dataclass(frozen=True)
class InferenceInputs:
    engine_mode: str
    difficulty: str
    elements_skeleton: List[Dict[str, Any]]
    canonical_payload: Dict[str, Any]
    canonical_row: Dict[str, Any]
    player: PlayerContext


@dataclass(frozen=True)
class InferenceOutputs:
    ranking_weights: Dict[str, float]
    element_ordering: Optional[List[str]]
    narrative_template_id: Optional[str]
    variant_id: Optional[str]
    bandit_meta: Optional[Dict[str, Any]]

    def to_dict(self) -> Dict[str, Any]:
        out: Dict[str, Any] = {
            "ranking_weights": dict(self.ranking_weights or {}),
        }
        if self.element_ordering is not None:
            out["element_ordering"] = list(self.element_ordering)
        if self.narrative_template_id is not None:
            out["narrative_template_id"] = self.narrative_template_id
        if self.variant_id is not None:
            out["variant_id"] = self.variant_id
        if self.bandit_meta is not None:
            out["bandit"] = dict(self.bandit_meta)
        return out


# ----------------------------
# Ranking Model (bounded)
# ----------------------------

class RankingModel:
    """Presentation-only ranking model.

    Default behavior is a safe heuristic:
    - weight = 1 + 0.5 * dominant_score_norm

    Callers may inject a model callback in the future; this class remains an interface.
    """

    def __init__(self, *, enabled: bool = True):
        self.enabled = bool(enabled)

    def infer_weights(self, elements: Sequence[Dict[str, Any]]) -> Dict[str, float]:
        if not self.enabled or not elements:
            return {}

        # Use dominant_score if present else score * section_coverage
        dom_scores: List[Tuple[str, float]] = []
        for el in elements:
            eid = str(el.get("element_id") or el.get("element_name") or "")
            if not eid:
                continue
            score = float(el.get("score", 0.0) or 0.0)
            cov = float(el.get("section_coverage", 0.0) or 0.0)
            dom = float(el.get("dominant_score", score * cov))
            dom_scores.append((eid, dom))

        if not dom_scores:
            return {}

        vals = [v for _, v in dom_scores]
        vmin, vmax = min(vals), max(vals)
        denom = (vmax - vmin) if (vmax - vmin) > 1e-9 else 1.0

        weights: Dict[str, float] = {}
        for eid, v in dom_scores:
            norm = (v - vmin) / denom
            # bounded range [1.0, 1.5]
            weights[eid] = 1.0 + 0.5 * float(max(0.0, min(1.0, norm)))
        return weights

    def infer_ordering(self, elements: Sequence[Dict[str, Any]], weights: Dict[str, float]) -> Optional[List[str]]:
        if not self.enabled or not elements or not weights:
            return None
        # order by weighted dominant score
        scored: List[Tuple[str, float]] = []
        for el in elements:
            eid = str(el.get("element_id") or el.get("element_name") or "")
            if not eid:
                continue
            score = float(el.get("score", 0.0) or 0.0)
            cov = float(el.get("section_coverage", 0.0) or 0.0)
            dom = float(el.get("dominant_score", score * cov))
            w = float(weights.get(eid, 1.0))
            scored.append((eid, dom * w))

        if not scored:
            return None

        scored_sorted = sorted(scored, key=lambda kv: (-kv[1], kv[0]))
        return [eid for eid, _ in scored_sorted]


# ----------------------------
# Template Selector (bounded)
# ----------------------------

class TemplateSelector:
    """Selects a narrative template ID from an allow-list registry.

    The registry format is caller-provided to keep this module IO-free.
    Example registry:
      {
        "expert": ["template_expert_v3_A", "template_expert_v3_B"],
        "master": ["template_master_v3_A"],
        "append": ["template_append_v3_A"]
      }
    """

    def __init__(self, template_registry: Optional[Dict[str, List[str]]] = None):
        self.registry = template_registry or {}

    def select(self, *, difficulty: str, locale: Optional[str] = None) -> Optional[str]:
        diff = (difficulty or "").strip().lower()
        cands = self.registry.get(diff) or []
        if not cands:
            return None
        # Deterministic-ish selection without external features: pick first
        # (Callers may later override with a model.)
        return str(cands[0])


# ----------------------------
# Bandit Policy (constrained exploration)
# ----------------------------

class BanditPolicy:
    """Constrained exploration over variants.

    Uses epsilon-greedy over a list of allowed variants.
    No online learning: rewards are not updated here.
    """

    def __init__(self, *, epsilon: float = 0.1, seed: Optional[int] = None):
        self.epsilon = float(max(0.0, min(1.0, epsilon)))
        self._rng = random.Random(seed)

    def choose_variant(
        self,
        *,
        allowed_variants: Sequence[str],
        preferred_variant: Optional[str] = None,
        engine_mode: str = "personalized",
    ) -> Tuple[Optional[str], Dict[str, Any]]:
        mode = (engine_mode or "").strip().lower()
        variants = [str(v) for v in (allowed_variants or []) if str(v)]
        if not variants or mode == "deterministic":
            return None, {"policy": "epsilon_greedy", "epsilon": self.epsilon, "chosen": None}

        pref = str(preferred_variant) if preferred_variant else None

        explore = self._rng.random() < self.epsilon
        if explore:
            chosen = self._rng.choice(variants)
            reason = "exploration"
        else:
            chosen = pref if (pref in variants) else variants[0]
            reason = "exploit_preferred" if (pref and pref in variants) else "exploit_default"

        return chosen, {"policy": "epsilon_greedy", "epsilon": self.epsilon, "chosen": chosen, "reason": reason}


# ----------------------------
# Orchestrated inference call
# ----------------------------

def run_phase4_model_inference(
    inputs: InferenceInputs,
    *,
    ranking_model: Optional[RankingModel] = None,
    template_selector: Optional[TemplateSelector] = None,
    bandit_policy: Optional[BanditPolicy] = None,
    variant_registry: Optional[Dict[str, List[str]]] = None,
) -> InferenceOutputs:
    """Run bounded Phase‑4 model inference.

    Returns advisory outputs only. Callers must still validate and apply via Safe Adjustment Interface.
    """

    mode = (inputs.engine_mode or "").strip().lower()
    if mode == "deterministic":
        return InferenceOutputs({}, None, None, None, {"bypassed": True})

    rm = ranking_model or RankingModel(enabled=True)
    ts = template_selector or TemplateSelector(template_registry={})
    bp = bandit_policy or BanditPolicy(epsilon=0.1)

    weights = rm.infer_weights(inputs.elements_skeleton)
    ordering = rm.infer_ordering(inputs.elements_skeleton, weights)

    template_id = ts.select(difficulty=inputs.difficulty, locale=inputs.player.locale)

    # Variants are constrained by registry: {template_id: [variant_id...]}
    vr = variant_registry or {}
    allowed_variants = vr.get(template_id or "") or []
    variant_id, bandit_meta = bp.choose_variant(
        allowed_variants=allowed_variants,
        preferred_variant=None,
        engine_mode=mode,
    )

    return InferenceOutputs(
        ranking_weights=weights,
        element_ordering=ordering,
        narrative_template_id=template_id,
        variant_id=variant_id,
        bandit_meta=bandit_meta,
    )


__all__ = [
    "PlayerContext",
    "InferenceInputs",
    "InferenceOutputs",
    "RankingModel",
    "TemplateSelector",
    "BanditPolicy",
    "run_phase4_model_inference",
]
