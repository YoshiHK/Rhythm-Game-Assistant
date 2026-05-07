from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .decision_rules import evaluate_gates


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def decide_personalization(
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
    decision_interface_version: str = "v1",
) -> Dict[str, Any]:
    """
    Phase 4 Decision Engine (single authority).

    Implements the Personalization Decision Interface:
    - Deterministically decides whether personalization is allowed
    - Emits presentation-only adjustment directives (may be empty)
    - Produces provenance-friendly decision record

    Hard constraints:
    - Must not modify Phase 1–3 semantics or artifacts
    - Must not generate free-form text
    - Must not perform model inference here
    """

    gates = evaluate_gates(
        engine_mode=engine_mode,
        opt_in=opt_in,
        feature_flags=feature_flags,
    )

    provenance: Dict[str, Any] = {
        "engine_mode": engine_mode,
        "decision_timestamp": _utc_now_iso(),
        "decision_interface_version": decision_interface_version,
        "gates": gates,
        # Decision source is rule by default; inference layer may later mark hybrid/model elsewhere
        "decision_source": "rule",
    }

    if not gates["personalization_allowed"]:
        return {
            "personalization_allowed": False,
            "gate_fail_reasons": gates.get("gate_fail_reasons", []),
            "adjustment_directives": {},
            "decision_source": "rule",
            "provenance": provenance,
            "locale": locale,
        }

    # Wave-1 default: allow personalization but do not force directives
    # (Directives may be supplied by registry/model inference later)
    return {
        "personalization_allowed": True,
        "gate_fail_reasons": [],
        "adjustment_directives": {},
        "decision_source": "rule",
        "provenance": provenance,
        "locale": locale,
    }


__all__ = ["decide_personalization"]