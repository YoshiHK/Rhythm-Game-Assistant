from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

# ✅ Runtime routers (execution spine) — absolute imports (PYTHONPATH = Phase 4 - Personalization)
from runtime.decision_router import run_personalization_decision
from runtime.inference_router import run_model_inference
from runtime.adjustment_router import apply_adjustments

# ✅ Narrative (presentation-only) — absolute import per routing skeleton
from narrative.narrative_v3_bridge import generate_tips_text_v3


@dataclass(frozen=True)
class Phase4RuntimeConfig:
    """
    Phase 4 runtime configuration (design-locked).

    NOTE:
    - Must remain deterministic for identical inputs.
    - Volatile timestamps are scrubbed by CI determinism fixtures.
    """
    decision_interface_version: str = "v1"
    include_experimental_variants: bool = False


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def run_phase4_personalization(
    *,
    canonical_payload: Dict[str, Any],
    canonical_row: Dict[str, Any],
    elements_skeleton: List[Dict[str, Any]],
    difficulty: str,
    engine_mode: str = "deterministic",
    locale: Optional[str] = None,
    player_context: Optional[Dict[str, Any]] = None,
    feature_flags: Optional[Dict[str, Any]] = None,
    opt_in: Optional[bool] = None,
    orchestrator_ext: Optional[Dict[str, Any]] = None,  # record-only
    cfg: Phase4RuntimeConfig = Phase4RuntimeConfig(),
) -> Dict[str, Any]:
    """
    Phase 4 — Personalization Runtime Entry Point.

    Contract:
    - MUST NOT mutate semantic fields from Phase 1–3 outputs.
    - MAY adjust ordering/presentation only (bounded).
    - MUST emit explainability provenance chain.
    """

    # 1) Decision: rule/model/hybrid
    decision = run_personalization_decision(
        canonical_payload=canonical_payload,
        canonical_row=canonical_row,
        elements_skeleton=elements_skeleton,
        difficulty=difficulty,
        engine_mode=engine_mode,
        locale=locale,
        player_context=player_context,
        feature_flags=feature_flags,
        opt_in=opt_in,
        decision_interface_version=cfg.decision_interface_version,
    )

    # 2) Inference: only for model/hybrid (router should no-op for rule)
    inf = run_model_inference(
        decision=decision,
        canonical_payload=canonical_payload,
        elements_skeleton=elements_skeleton,
        include_experimental_variants=cfg.include_experimental_variants,
    )
    adjustment_directives = inf.get("adjustment_directives") or {}

    # 3) Apply safe adjustments (presentation-only)
    adj = apply_adjustments(
        base_elements=elements_skeleton,
        base_narrative=None,
        adjustment_directives=adjustment_directives,
        provenance={"decision_timestamp": _utc_now_iso()},
    )

    elements_view = adj["elements_view"]
    applied_adjustments = adj["applied_adjustments"]

    # 4) Narrative v3 bridge (presentation-only)
    narrative = generate_tips_text_v3(
        canonical_payload=canonical_payload,
        canonical_row=canonical_row,
        elements_view=elements_view,
        difficulty=difficulty,
        locale=locale,
    )

    # 5) Provenance (spec §7.2 chain)
    phase4_provenance = {
        "engine_mode": engine_mode,
        "decision_timestamp": _utc_now_iso(),
        "decision_interface_version": cfg.decision_interface_version,
        "gates": {"personalization_allowed": True},
        "decision_source": decision.get("decision_source", "rule"),
        "adjustments": applied_adjustments if applied_adjustments else {},
        "model_metadata": decision.get("model_metadata"),
    }

    out: Dict[str, Any] = {
        "elements_view": elements_view,
        "model_outputs": decision.get("model_outputs") or {},
        "applied_adjustments": applied_adjustments or {},
        "phase4_provenance": phase4_provenance,
        "narrative": narrative,
    }

    # record-only passthrough
    if orchestrator_ext is not None:
        out["orchestrator_ext"] = orchestrator_ext

    return out
