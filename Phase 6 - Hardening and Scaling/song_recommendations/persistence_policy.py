"""
Phase 6 Song Recommendations — Persistence Policy (save/refresh + rotation plan)

Purpose
-------
Produce a persistence plan (create payloads + delete IDs) without performing I/O.

Design constraints:
- deterministic
- policy-only (platform-owned)
- no database writes here
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Sequence, Tuple

from request_normalizer import NormalizedSongRecRequest, RecentRecommendation


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
    - Only delete non-bookmarked entries
    - Delete oldest first (created_at)
    - Deterministic tie-break by record_id
    - Skip entries without record_id
    """
    if max_history <= 0:
        return []

    total_after = len(recent) + incoming_count
    if total_after <= max_history:
        return []

    candidates: List[Tuple[float, str]] = []
    for r in recent:
        if r.bookmarked:
            continue
        if not r.record_id:
            continue
        candidates.append((_parse_iso(r.created_at), r.record_id))

    candidates.sort(key=lambda x: (x[0], x[1]))
    to_delete = min(len(candidates), total_after - max_history)
    return [rid for _, rid in candidates[:to_delete]]


def build_create_payloads(req: NormalizedSongRecRequest, items: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Build store-agnostic create payloads.

    A storage adapter can map these fields to Softr/Airtable IDs later.
    """
    out: List[Dict[str, Any]] = []
    for it in items:
        out.append(
            {
                "game_id": req.game_id,
                "player_id_hash": req.player_id_hash,
                "song_id": it.get("song_id"),
                "song_name": it.get("song_name"),
                "producer_name": it.get("producer_name"),
                "difficulty": it.get("difficulty"),
                "level": it.get("level"),
                "recommendation_type": it.get("recommendation_type"),
                "rationale": it.get("rationale"),
                "is_active": True,
                "bookmarked": False,
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
    action="refresh" → no persistence
    action="save"    → return create payloads + rotation deletion plan
    """
    if req.action != "save":
        return PersistencePlan(did_save=False, create_records=[], delete_ids=[], delete_count=0)

    create_records = build_create_payloads(req, items)
    delete_ids = build_rotation_deletions(req.recent_recommendations, incoming_count=len(create_records), max_history=max_history)

    return PersistencePlan(
        did_save=True,
        create_records=create_records,
        delete_ids=delete_ids,
        delete_count=len(delete_ids),
    )