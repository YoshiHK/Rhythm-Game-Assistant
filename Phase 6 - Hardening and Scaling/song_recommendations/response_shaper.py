"""
Phase 6 Song Recommendations — Response Shaper

Purpose
-------
Assemble API-safe response objects for mode="songs".

Design constraints:
- deterministic
- no I/O
- does not rank or localize
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, List

from request_normalizer import NormalizedSongRecRequest
from persistence_policy import PersistencePlan


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
    """Return final response dict for mode='songs'."""

    # Ensure JSON-serializable (defensive)
    try:
        json.dumps(items, ensure_ascii=False)
    except Exception:
        safe_items: List[Dict[str, Any]] = []
        for it in items:
            safe_items.append({k: v for k, v in it.items() if isinstance(k, str)})
        items = safe_items

    set_obj = {
        "game_id": req.game_id,
        "mode": req.mode,
        "locale": req.locale,
        "max_items": req.max_items,
        "items": items,
    }
    set_id = _stable_id(set_obj)

    return {
        "mode": "songs",
        "status": status,
        "recommendation_set": {
            "set_id": set_id,
            "items": items,
        },
        "persistence": {
            "did_save": persistence.did_save,
            "created_count": len(persistence.create_records),
            "create_records": persistence.create_records,
            "delete_ids": persistence.delete_ids,
            "delete_count": persistence.delete_count,
        },
        "diagnostics": diagnostics,
    }
