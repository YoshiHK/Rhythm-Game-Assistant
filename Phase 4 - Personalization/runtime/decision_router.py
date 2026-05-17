from __future__ import annotations
from typing import Any, Dict, List, Optional

from decision.decision_engine import decide_personalization


def run_personalization_decision(
    *,
    canonical_payload: Dict[str, Any],
    canonical_row: Dict[str, Any],
    elements_skeleton: List[Dict[str, Any]],
    difficulty: str,
    engine_mode: str,
    locale: Optional[str],
    player_context: Optional[Dict[str, Any]],
    feature_flags: Optional[Dict[str, Any]],
    opt_in: Optional[bool],
    decision_interface_version: str,
) -> Dict[str, Any]:
    """Runtime adapter for Phase 4 Personalization Decision."""
    return decide_personalization(
        canonical_payload=canonical_payload,
        canonical_row=canonical_row,
        elements_skeleton=elements_skeleton,
        difficulty=difficulty,
        engine_mode=engine_mode,
        locale=locale,
        player_context=player_context,
        feature_flags=feature_flags,
        opt_in=opt_in,
        decision_interface_version=decision_interface_version,
    )