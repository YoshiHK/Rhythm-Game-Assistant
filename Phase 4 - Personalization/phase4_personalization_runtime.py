
#!/usr/bin/env python3
"""phase4_personalization_runtime.py

Phase 4 Integration Shim (runtime wiring).

Wires together Phase 4 components without modifying any completed phases:
- Template registry loader
- Model inference layer (ranking + template selector + bandit)
- Safe adjustment application
- Narrative module v3 rendering
- Provenance assembly (Phase 4 provenance dict)
- Event log builder helper (PHASE_4_EVENT_LOG.schema.json)

This module is intentionally conservative:
- Deterministic fallback is always available.
- No online learning.
- No event/feedback persistence (callers log externally using schemas).
- No mutation of Phase 2/3 artifacts.

Expected local modules (created in this project):
- phase4_template_registry_loader.py
- phase4_model_inference.py
- safe_adjustment.py
- narrative_module_v3.py

"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone

from phase4_template_registry_loader import load_phase4_template_registry
from phase4_model_inference import (
    PlayerContext,
    InferenceInputs,
    run_phase4_model_inference,
    TemplateSelector,
)
from safe_adjustment import apply_safe_adjustments
from narrative_module_v3 import generate_tips_text_v3


@dataclass(frozen=True)
class Phase4RuntimeConfig:
    template_registry_path: str = "PHASE_4_TEMPLATE_REGISTRY_STARTER.json"
    include_experimental_variants: bool = False


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ----------------------------
# Phase 4 provenance builder
# ----------------------------

def build_phase4_provenance(
    *,
    engine_mode: str,
    personalization_allowed: bool,
    gate_fail_reasons: Optional[List[str]] = None,
    decision_source: str = "rule",
    model_id: Optional[str] = None,
    model_version: Optional[str] = None,
    model_role: Optional[str] = None,
    adjustments: Optional[Dict[str, Any]] = None,
    template_id: Optional[str] = None,
    variant_id: Optional[str] = None,
    why_personalized: Optional[str] = None,
    why_template: Optional[str] = None,
    why_variant: Optional[str] = None,
) -> Dict[str, Any]:
    """Assemble a Phase 4 provenance dict consistent with PHASE_4_PROVENANCE.schema.json.

    This helper only builds the dict; schema validation can be done in CI.
    """
    prov: Dict[str, Any] = {
        "engine_mode": (engine_mode or "deterministic").strip().lower(),
        "decision_timestamp": _utc_now_iso(),
        "gates": {
            "personalization_allowed": bool(personalization_allowed),
            "gate_fail_reasons": list(gate_fail_reasons or []),
        },
        "decision_source": (decision_source or "rule").strip().lower(),
    }

    if model_id or model_version or model_role:
        prov["model_metadata"] = {
            "model_id": model_id,
            "model_version": model_version,
            "model_role": model_role,
        }

    if adjustments:
        prov["adjustments"] = dict(adjustments)

    if template_id or variant_id:
        prov.setdefault("adjustments", {})
        if template_id:
            prov["adjustments"]["narrative_template_id"] = template_id
        if variant_id:
            prov["adjustments"]["variant_id"] = variant_id

    if any([why_personalized, why_template, why_variant]):
        prov["explainability"] = {
            "why_personalized": why_personalized or "",
            "why_template": why_template or "",
            "why_variant": why_variant or "",
        }

    return prov


# ----------------------------
# Event log builder helper
# ----------------------------

def build_phase4_event_log_entry(
    *,
    event_id: str,
    event_type: str,
    request_id: str,
    payload_hash: str,
    game_id: str,
    song_id: Optional[Any] = None,
    difficulty_label: Optional[str] = None,
    engine_mode: Optional[str] = None,
    session_id: Optional[str] = None,
    player_id_hash: Optional[str] = None,
    locale: Optional[str] = None,
    app_version: Optional[str] = None,
    model_bundle_version: Optional[str] = None,
    feature_flags: Optional[Dict[str, Any]] = None,
    decision: Optional[Dict[str, Any]] = None,
    ui: Optional[Dict[str, Any]] = None,
    feedback: Optional[Dict[str, Any]] = None,
    outcome: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Build an event log record conforming to PHASE_4_EVENT_LOG.schema.json.

    Notes
    -----
    - This helper only builds the dict; it does not persist logs.
    - No raw canonical payload is stored, only payload_hash.
    """

    evt: Dict[str, Any] = {
        "event_id": str(event_id),
        "event_type": str(event_type),
        "event_timestamp": _utc_now_iso(),
        "request": {
            "request_id": str(request_id),
            "payload_hash": str(payload_hash),
        },
        "context": {
            "game_id": str(game_id),
        },
    }

    # request optional fields
    if session_id:
        evt["request"]["session_id"] = str(session_id)
    if player_id_hash:
        evt["request"]["player_id_hash"] = str(player_id_hash)
    if engine_mode:
        evt["request"]["engine_mode"] = str(engine_mode)
    if locale:
        evt["request"]["locale"] = str(locale)

    # context optional fields
    if song_id is not None:
        evt["context"]["song_id"] = song_id
    if difficulty_label:
        evt["context"]["difficulty_label"] = str(difficulty_label)
    if app_version:
        evt["context"]["app_version"] = str(app_version)
    if model_bundle_version:
        evt["context"]["model_bundle_version"] = str(model_bundle_version)
    if feature_flags:
        evt["context"]["feature_flags"] = dict(feature_flags)

    # Optional sections
    if decision:
        evt["decision"] = dict(decision)
    if ui:
        evt["ui"] = dict(ui)
    if feedback:
        evt["feedback"] = dict(feedback)
    if outcome:
        evt["outcome"] = dict(outcome)

    return evt


# ----------------------------
# End-to-end personalization runtime
# ----------------------------

def run_phase4_personalization(
    *,
    canonical_payload: Dict[str, Any],
    canonical_row: Dict[str, Any],
    selected_elements: List[Dict[str, Any]],
    difficulty: str,
    engine_mode: str = "deterministic",
    player_id_hash: Optional[str] = None,
    locale: Optional[str] = None,
    feature_flags: Optional[Dict[str, Any]] = None,
    opt_in: Optional[bool] = None,
    cfg: Phase4RuntimeConfig = Phase4RuntimeConfig(),
) -> Dict[str, Any]:
    """End-to-end Phase 4 runtime shim.

    Returns:
      - tips_text
      - elements_view
      - narrative_metadata
      - phase4_provenance
      - model_outputs
      - applied_adjustments
      - gate_fail_reasons
    """

    mode = (engine_mode or "deterministic").strip().lower()

    # 1) deterministic gates
    flags = feature_flags or {}
    phase4_enabled = bool(flags.get("phase4_enabled", True))

    gate_fail_reasons: List[str] = []
    if not phase4_enabled:
        gate_fail_reasons.append("FLAG_DISABLED")
    if opt_in is False:
        gate_fail_reasons.append("OPT_OUT")

    personalization_allowed = (mode == "personalized") and phase4_enabled and (opt_in is not False)
    apply_personalization = personalization_allowed and (mode != "debug")

    # 2) baseline narrative always exists
    baseline = generate_tips_text_v3(
        difficulty=difficulty,
        selected_elements=selected_elements,
        engine_mode="deterministic" if mode != "personalized" else "personalized",
        narrative_template_id=None,
        variant_id=None,
        locale=locale,
    )

    elements_view = list(selected_elements)
    model_out: Dict[str, Any] = {}
    applied_adjustments: Dict[str, Any] = {}
    template_id: Optional[str] = None
    variant_id: Optional[str] = None

    # 3) optional model inference
    if (mode in ("personalized", "debug")) and phase4_enabled:
        loaded = load_phase4_template_registry(
            registry_path=cfg.template_registry_path,
            locale=locale,
            include_experimental_variants=cfg.include_experimental_variants,
        )

        ts = TemplateSelector(template_registry=loaded.template_registry)

        inputs = InferenceInputs(
            engine_mode=mode,
            difficulty=difficulty,
            elements_skeleton=selected_elements,
            canonical_payload=canonical_payload,
            canonical_row=canonical_row,
            player=PlayerContext(player_id_hash=player_id_hash, locale=locale),
        )

        inf = run_phase4_model_inference(
            inputs,
            template_selector=ts,
            variant_registry=loaded.variant_registry,
        )

        model_out = inf.to_dict()
        template_id = inf.narrative_template_id
        variant_id = inf.variant_id

        # 4) apply safe adjustments
        if apply_personalization:
            adj = {
                "element_ordering": model_out.get("element_ordering"),
                "ranking_weights": model_out.get("ranking_weights"),
            }
            safe = apply_safe_adjustments(selected_elements, adj)
            elements_view = safe.get("elements_view", list(selected_elements))
            applied_adjustments = safe.get("applied_adjustments", {})

            rendered = generate_tips_text_v3(
                difficulty=difficulty,
                selected_elements=elements_view,
                engine_mode=mode,
                narrative_template_id=template_id,
                variant_id=variant_id,
                locale=locale,
            )
        else:
            rendered = baseline
    else:
        rendered = baseline

    # 5) provenance
    prov = build_phase4_provenance(
        engine_mode=mode,
        personalization_allowed=bool(personalization_allowed),
        gate_fail_reasons=gate_fail_reasons,
        decision_source="model" if model_out else "rule",
        adjustments=applied_adjustments if applied_adjustments else None,
        template_id=template_id,
        variant_id=variant_id,
        why_personalized="" if apply_personalization else "Personalization not applied; deterministic output used.",
        why_template=f"Selected template {template_id}" if template_id else None,
        why_variant=f"Selected variant {variant_id}" if variant_id else None,
    )

    return {
        "tips_text": rendered.get("tips_text", ""),
        "elements_view": elements_view,
        "narrative_metadata": rendered.get("narrative_metadata", {}),
        "phase4_provenance": prov,
        "model_outputs": model_out,
        "applied_adjustments": applied_adjustments,
        "gate_fail_reasons": gate_fail_reasons,
    }


__all__ = [
    "Phase4RuntimeConfig",
    "build_phase4_provenance",
    "build_phase4_event_log_entry",
    "run_phase4_personalization",
]
