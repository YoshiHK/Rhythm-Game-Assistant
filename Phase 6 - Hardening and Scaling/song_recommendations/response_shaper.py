from __future__ import annotations

"""
Phase 6 Song Recommendations — Response Shaper

Purpose:
Assemble API-safe response objects for mode="songs".

Design constraints:
- deterministic
- no I/O
- does not rank or localize (ordering must be provided upstream)
- learning-loop-ready via additive exposure metadata (no semantics)
"""

import hashlib
import json
from typing import Any, Dict, List

from .request_normalizer import NormalizedSongRecRequest
from .persistence_policy import PersistencePlan


def _stable_id(obj: Dict[str, Any]) -> str:
    """Generate deterministic short id for a set payload."""
    text = json.dumps(obj, sort_keys=True, ensure_ascii=True, separators=(",", ":"))
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def shape_song_recommendation_response(
    req: NormalizedSongRecRequest,
    *,
    items: List[Dict[str, Any]],
    persistence: PersistencePlan,
    diagnostics: Dict[str, Any],
    status: str = "OK",
) -> Dict[str, Any]:
    """
    Return final response dict for mode='songs'.
    """
    rec_set_payload = {
        "game_id": req.game_id,
        "mode": req.mode,
        "action": req.action,
        "items": items,
        "player_id_hash": req.player_id_hash,
    }

    set_id = _stable_id(rec_set_payload)

    return {
        "mode": "songs",
        "status": status,
        "recommendation_set": {
            "set_id": set_id,
            "items": items,
        },
        "persistence": {
            "did_save": persistence.did_save,
            "delete_ids": persistence.delete_ids,
            "delete_count": persistence.delete_count,
        },
        "diagnostics": diagnostics or {},
    }


__all__ = ["shape_song_recommendation_response"]