from __future__ import annotations

from typing import Any, Dict, List, Optional


def evaluate_gates(
    *,
    engine_mode: str,
    opt_in: Optional[bool],
    feature_flags: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Deterministic gate evaluation for Phase 4 personalization.

    Returns:
      {
        "personalization_allowed": bool,
        "gate_fail_reasons": [str]
      }
    """
    reasons: List[str] = []

    if engine_mode != "personalized":
        reasons.append("ENGINE_MODE_NOT_PERSONALIZED")

    if opt_in is not True:
        reasons.append("PLAYER_NOT_OPTED_IN")

    if not (feature_flags and feature_flags.get("personalization_enabled")):
        reasons.append("FEATURE_FLAG_DISABLED")

    return {
        "personalization_allowed": len(reasons) == 0,
        "gate_fail_reasons": reasons,
    }