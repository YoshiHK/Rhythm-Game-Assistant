"""
Phase 6 Song Recommendations — Request Normalizer (non-semantic, CI-safe)

Purpose
-------
Normalize client-provided song recommendation requests into a canonical shape.

Design-Locked properties:
- Multi-game safe: does not hardcode difficulty names or completion labels
- Deterministic: identical input -> identical normalized output
- No runtime I/O

Non-goals:
- ranking / selection
- reading external databases
- locale inference

Upstream:
- Phase 6 router/auth/guards already applied

Downstream:
- game_capability_resolver resolves tier/ladder ordering
- song_rec_coordinator coordinates deterministic generation
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional


class ContractError(ValueError):
    """Raised when request violates the song recommendation contract."""


def _as_str(x: Any) -> Optional[str]:
    if x is None:
        return None
    if isinstance(x, str):
        s = x.strip()
        return s if s else None
    return str(x).strip() or None


def _as_int(x: Any, default: int = 0) -> int:
    try:
        n = int(x)
        return n if n >= 0 else default
    except Exception:
        return default


def _as_bool(x: Any, default: bool = False) -> bool:
    if isinstance(x, bool):
        return x
    if isinstance(x, (int, float)):
        return bool(x)
    if isinstance(x, str):
        v = x.strip().lower()
        if v in {"true", "1", "yes", "y"}:
            return True
        if v in {"false", "0", "no", "n"}:
            return False
    return default


@dataclass(frozen=True)
class RecentRecommendation:
    # song_id should be canonical (stable id), not song_name (multi-locale safe)
    song_id: Optional[str]
    bookmarked: bool = False
    created_at: Optional[str] = None  # ISO string if provided
    record_id: Optional[str] = None   # external store id (optional)


@dataclass(frozen=True)
class NormalizedSubmission:
    # Each tier entry is game-scoped. Phase 6 treats tier_id as opaque.
    # counts: {completion_id -> non-negative int}
    tiers: List[Dict[str, Any]]


@dataclass(frozen=True)
class NormalizedSongRecRequest:
    game_id: str
    mode: str  # must be "songs" here
    locale: Optional[str]
    max_items: int
    action: str  # "refresh" | "save"
    player_id_hash: Optional[str]
    submission: NormalizedSubmission
    recent_recommendations: List[RecentRecommendation]
    client: Dict[str, Any]


def normalize_song_recommendation_request(payload: Dict[str, Any]) -> NormalizedSongRecRequest:
    """
    Normalize request payload into canonical, validation-checked structure.

    Expected logical shape:
    - game_id, mode="songs", locale
    - submission.difficulty_progress.tiers = [{tier_id, counts:{completion_id:int}}]
    - action = refresh|save (save enables persistence policy downstream)
    - recent_recommendations = list of {song_id, bookmarked, created_at, record_id}
    """
    if not isinstance(payload, dict):
        raise ContractError("request payload must be an object")

    game_id = _as_str(payload.get("game_id"))
    if not game_id:
        raise ContractError("game_id is required")

    mode = _as_str(payload.get("mode")) or "songs"
    if mode != "songs":
        raise ContractError(f"invalid mode for song recommendations: {mode!r}")

    locale = _as_str(payload.get("locale"))

    max_items = _as_int(payload.get("max_items"), default=3)
    if max_items <= 0:
        max_items = 3

    action = (_as_str(payload.get("action")) or "refresh").lower()
    if action not in {"refresh", "save"}:
        raise ContractError("action must be 'refresh' or 'save'")

    player_id_hash = _as_str(payload.get("player_id_hash"))

    sub = payload.get("submission")
    if not isinstance(sub, dict):
        raise ContractError("submission must be an object")

    dp = sub.get("difficulty_progress")
    if not isinstance(dp, dict):
        raise ContractError("submission.difficulty_progress must be an object")

    tiers = dp.get("tiers")
    if not isinstance(tiers, list) or not tiers:
        raise ContractError("submission.difficulty_progress.tiers must be a non-empty list")

    norm_tiers: List[Dict[str, Any]] = []
    for t in tiers:
        if not isinstance(t, dict):
            continue
        tier_id = _as_str(t.get("tier_id"))
        counts = t.get("counts")
        if not tier_id or not isinstance(counts, dict):
            continue

        norm_counts: Dict[str, int] = {}
        for k, v in counts.items():
            ck = _as_str(k)
            if not ck:
                continue
            norm_counts[ck] = _as_int(v, default=0)

        if not norm_counts:
            continue

        norm_tiers.append({"tier_id": tier_id, "counts": norm_counts})

    if not norm_tiers:
        raise ContractError("no valid tier entries found in submission")

    rr_raw = payload.get("recent_recommendations")
    rr_list: List[RecentRecommendation] = []
    if isinstance(rr_raw, list):
        for r in rr_raw:
            if not isinstance(r, dict):
                continue
            rr_list.append(
                RecentRecommendation(
                    song_id=_as_str(r.get("song_id")),
                    bookmarked=_as_bool(r.get("bookmarked"), default=False),
                    created_at=_as_str(r.get("created_at")),
                    record_id=_as_str(r.get("record_id")),
                )
            )

    client = payload.get("client")
    if not isinstance(client, dict):
        client = {}

    return NormalizedSongRecRequest(
        game_id=game_id,
        mode=mode,
        locale=locale,
        max_items=max_items,
        action=action,
        player_id_hash=player_id_hash,
        submission=NormalizedSubmission(tiers=norm_tiers),
        recent_recommendations=rr_list,
        client=client,
    )