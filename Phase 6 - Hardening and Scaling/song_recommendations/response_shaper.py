"""
Phase 6 Song Recommendations — Response Shaper

### Purpose

Assemble API-safe response objects for mode="songs".

Design constraints:
- deterministic
- no I/O
- does not rank or localize (ordering must be provided upstream)
- learning-loop-ready via additive exposure metadata (no semantics)
"""
from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, List

# Support both package and flat imports
try:
    from phase6.song_recommendation.request_normalizer import NormalizedSongRecRequest  # type: ignore
    from phase6.song_recommendation.persistence_policy import PersistencePlan  # type: ignore
except Exception:
    from request_normalizer import NormalizedSongRecRequest  # type: ignore
    from persistence_policy import PersistencePlan  # type: ignore


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

    Learning-loop readiness:
    - Adds stable set_id
    - Adds per-item rank (1-based) without changing order
    - Passes through diagnostics fields if provided (catalog_fingerprint, selection_window, reason codes)
    """
    # Defensive copy (no mutation of caller objects)
    safe_items: List[Dict[str, Any]] = []
    for i, it in enumerate(items):
        if not isinstance(it, dict):
            continue
        out = dict(it)
        # Add exposure rank (non-semantic; preserves existing order)
        out.setdefault("rank", i + 1)
        safe_items.append(out)

    recommendation_set_payload = {
        "game_id": getattr(req, "game_id", None),
        "mode": "songs",
        "action": getattr(req, "action", None),
        "items": [
            {
                "song_id": x.get("song_id"),
                "difficulty": x.get("difficulty"),
                "level": x.get("level"),
                "recommendation_type": x.get("recommendation_type"),
                "rank": x.get("rank"),
            }
            for x in safe_items
        ],
    }

    set_id = _stable_id(recommendation_set_payload)

    # Diagnostics passthrough (no inference)
    diag = dict(diagnostics) if isinstance(diagnostics, dict) else {}
    # Ensure stable identifiers exist for downstream learning/QA
    diag.setdefault("recommendation_set_id", set_id)
    diag.setdefault("game_id", getattr(req, "game_id", None))

    response: Dict[str, Any] = {
        "mode": "songs",
        "status": status,
        "recommendation_set": {
            "set_id": set_id,
            "items": safe_items,
        },
        "persistence": persistence if isinstance(persistence, dict) else dict(persistence),
        "diagnostics": diag,
    }

    return response