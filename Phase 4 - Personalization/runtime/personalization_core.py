from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone

# Runtime routers (execution spine)
from .decision_router import run_personalization_decision
from .inference_router import run_model_inference
from .adjustment_router import apply_adjustments

# Narrative (presentation-only)
from ..narrative import generate_tips_text_v3


@dataclass(frozen=True)
class Phase4RuntimeConfig:
    """
    Phase 4 runtime configuration.

    Note:
    - This config is NOT persisted.
    - CI may inject alternate configs for testing.
    """
    decision_interface_version: str = "v1"
    include_experimental_variants: bool = False

    # Phase 2 renderer inputs (pass-through only)
    tips_spec_path: str = "proseka_tips_generation_spec_v1.0.1_advisory.json"
    track_cd_config_path: str = "track_cd_config.json"


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

    Guarantees:
    - Deterministic fallback always available
    - No mutation of Phase 1–3 artifacts
    - Presentation-only personalization
    """

    # -------------------------
    # 1) Personalization decision (authoritative)
    # -------------------------
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

    provenance = dict(decision.get("provenance") or {})
    provenance.setdefault("decision_timestamp", _utc_now_iso())
    provenance.setdefault("engine_mode", engine_mode)
    provenance.setdefault("decision_interface_version", cfg.decision_interface_version)

    # -------------------------
    # 2) Deterministic fallback path
    # -------------------------
    if not decision.get("personalization_allowed", False):
        render = generate_tips_text_v3(
            difficulty=difficulty,
            selected_elements=list(elements_skeleton),
            engine_mode="deterministic",
            locale=locale,
            tips_spec_path=cfg.tips_spec_path,
            track_cd_config_path=cfg.track_cd_config_path,
            orchestrator_ext=orchestrator_ext,
        )

        provenance["safe_adjustment_applied"] = False

        return {
            "engine_mode": engine_mode,
            "elements_view": list(elements_skeleton),
            "tips_text": render["tips_text"],
            "render_metadata": render["render_metadata"],
            "provenance": provenance,
            # CI / observability hint
            "outcome": {
                "tips_generated": True,
                "fallback_used": True,
            },
        }

    # -------------------------
    # 3) Model inference (advisory)
    # -------------------------
    inference = run_model_inference(
        decision=decision,
        canonical_payload=canonical_payload,
        elements_skeleton=elements_skeleton,
        include_experimental_variants=cfg.include_experimental_variants,
    )

    adjustment_directives = dict(inference.get("adjustment_directives") or {})

    provenance["adjustments"] = {
        k: v
        for k, v in adjustment_directives.items()
        if k in (
            "element_ordering",
            "ranking_weights",
            "narrative_template_id",
            "variant_id",
        )
    }

    # -------------------------
    # 4) Safe adjustment (non-destructive)
    # -------------------------
    adjusted = apply_adjustments(
        base_elements=elements_skeleton,
        base_narrative=decision.get("base_narrative"),
        adjustment_directives=adjustment_directives,
        provenance=provenance,
    )

    elements_view = adjusted["elements_view"]
    applied_adjustments = adjusted["applied_adjustments"]
    provenance_out = adjusted["provenance"]

    # -------------------------
    # 5) Narrative v3 render (presentation-only)
    # -------------------------
    render = generate_tips_text_v3(
        difficulty=difficulty,
        selected_elements=list(elements_view),
        engine_mode=engine_mode,
        narrative_template_id=applied_adjustments.get("narrative_template_id"),
        variant_id=applied_adjustments.get("variant_id"),
        element_ordering=applied_adjustments.get("element_ordering"),
        locale=locale,
        tips_spec_path=cfg.tips_spec_path,
        track_cd_config_path=cfg.track_cd_config_path,
        orchestrator_ext=orchestrator_ext,
    )

    return {
        "engine_mode": engine_mode,
        "elements_view": elements_view,
        "applied_adjustments": applied_adjustments,
        "tips_text": render["tips_text"],
        "render_metadata": render["render_metadata"],
        "provenance": provenance_out,
        # CI / observability hint
        "outcome": {
            "tips_generated": True,
            "fallback_used": False,
        },
    }