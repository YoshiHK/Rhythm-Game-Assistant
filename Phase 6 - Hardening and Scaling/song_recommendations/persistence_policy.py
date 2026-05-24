from __future__ import annotations

"""
Phase 6 Song Recommendations — Persistence Policy (save/refresh + rotation plan)

Purpose:
- Produce a persistence plan (create payloads + delete IDs) without performing I/O.

Design constraints:
- deterministic
- policy-only (platform-owned)
- no database writes here
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Sequence

from .request_normalizer import NormalizedSongRecRequest, RecentRecommendation

FIXED_TIMESTAMP = "1970-01-01T00:00:00Z"

@dataclass(frozen=True)
class PersistencePlan:
    did_save: bool
    create_records: List[Dict[str, Any]]
    delete_ids: List[str]
    delete_count: int


def _parse_iso(ts: Optional[str]) -> float:
    if not ts:
        return 0.0
    try:
        t = ts.replace("Z", "+00:00")
        return datetime.fromisoformat(t).timestamp()
    except Exception:
        return 0.0


def build_rotation_deletions(
    recent: Sequence[RecentRecommendation],
    *,
    incoming_count: int,
    max_history: int = 10,
) -> List[str]:
    """
    Compute which record_ids to delete to keep history within max_history.

    Rules:
    - Never delete bookmarked items
    - Delete oldest first (created_at), stable tie-break by record_id
    """
    if incoming_count <= 0:
        return []

    keep_limit = max(0, int(max_history))
    # if we are going to add incoming_count items, ensure total <= keep_limit
    # delete_count = max(0, (len(existing_non_bookmarked) + incoming_count) - keep_limit)
    candidates = []
    for r in recent:
        if getattr(r, "bookmarked", False):
            continue
        rid = getattr(r, "record_id", None)
        if not rid:
            continue
        created = _parse_iso(getattr(r, "created_at", None))
        candidates.append((created, str(rid)))

    candidates.sort(key=lambda x: (x[0], x[1]))  # deterministic

    delete_count = max(0, (len(candidates) + int(incoming_count)) - keep_limit)
    if delete_count <= 0:
        return []
    return [rid for _, rid in candidates[:delete_count]]


def build_create_payloads(
    req: NormalizedSongRecRequest,
    items: Sequence[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Build store-agnostic create payloads (no I/O).
    """
    out: List[Dict[str, Any]] = []
    for it in items:
        out.append(
            {
                "player_id_hash": req.player_id_hash,
                "game_id": req.game_id,
                "song_id": it.get("song_id"),
                "created_at": FIXED_TIMESTAMP
            }
        )
    return out


def compute_persistence_plan(
    req: NormalizedSongRecRequest,
    items: Sequence[Dict[str, Any]],
    *,
    max_history: int = 10,
) -> PersistencePlan:
    """
    action="refresh" -> no persistence
    action="save"    -> return create payloads + rotation deletion plan
    """
    if req.action != "save":
        return PersistencePlan(did_save=False, create_records=[], delete_ids=[], delete_count=0)

    create_records = build_create_payloads(req, items)
    delete_ids = build_rotation_deletions(
        req.recent_recommendations,
        incoming_count=len(create_records),
        max_history=max_history,
    )
    return PersistencePlan(
        did_save=True,
        create_records=create_records,
        delete_ids=delete_ids,
        delete_count=len(delete_ids),
    )


__all__ = [
    "PersistencePlan",
    "compute_persistence_plan",
    "build_rotation_deletions",
]