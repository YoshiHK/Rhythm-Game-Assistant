from __future__ import annotations

"""
Phase 6 Song Recommendations — Coordinator

Coordinates mode="songs" recommendation generation as a Phase 6-owned wiring layer.

Design constraints:
- deterministic
- no I/O
- multi-game safe (no hardcoded tier/label semantics)
"""

from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Sequence, Set, Tuple

from .request_normalizer import NormalizedSongRecRequest
from .game_capability_resolver import (
    GameCapability,
    canonicalize_completion_id,
    canonicalize_tier_id,
)


@dataclass(frozen=True)
class Target:
    tier_id: str
    completion_id: str
    target_count: int


def _sum_counts(counts: Dict[str, int]) -> int:
    return sum(int(v) for v in counts.values() if isinstance(v, int) and v >= 0)


def compute_targets_from_submission(req: NormalizedSongRecRequest, cap: GameCapability) -> Dict[str, Target]:
    """
    Compute three targets for a recommendation set (Clear/FC/AP)
    using ladder ordering and tier normalization.
    """
    # Minimal deterministic mapping: pick first tier from submission if present; otherwise first cap tier
    tier_id = cap.difficulty_tiers[0] if cap.difficulty_tiers else ""
    if req.submission.tiers:
        raw_tier = req.submission.tiers[0].get("tier_id")
        if raw_tier:
            tier_id = canonicalize_tier_id(cap, str(raw_tier))

    # Determine ladder positions (bottom/mid/top)
    ladder = list(cap.completion_ladder)
    if len(ladder) < 2:
        ladder = ["clear", "ap"]

    clear = canonicalize_completion_id(cap, ladder[0])
    ap = canonicalize_completion_id(cap, ladder[-1])
    fc = canonicalize_completion_id(cap, ladder[len(ladder)//2])

    return {
        "clear": Target(tier_id=tier_id, completion_id=clear, target_count=1),
        "fc": Target(tier_id=tier_id, completion_id=fc, target_count=1),
        "ap": Target(tier_id=tier_id, completion_id=ap, target_count=1),
    }


def build_exclusion_set(req: NormalizedSongRecRequest) -> Set[str]:
    out: Set[str] = set()
    for r in req.recent_recommendations:
        if r.song_id:
            out.add(r.song_id)
    return out


SongSelector = Callable[[Target, Set[str]], Optional[Dict[str, Any]]]


def generate_recommendation_items(
    req: NormalizedSongRecRequest,
    cap: GameCapability,
    *,
    selector: SongSelector,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Generate up to 3 items using injected selector.
    Determinism must be enforced by selector implementation.
    """
    excluded = build_exclusion_set(req)
    targets = compute_targets_from_submission(req, cap)

    items: List[Dict[str, Any]] = []
    for key in ("ap", "fc", "clear"):
        t = targets[key]
        picked = selector(t, excluded)
        if picked is None:
            continue
        items.append(dict(picked))
        sid = picked.get("song_id")
        if isinstance(sid, str) and sid:
            excluded.add(sid)

    diagnostics = {"excluded_count": len(build_exclusion_set(req)), "items_count": len(items)}
    return items, diagnostics


__all__ = ["Target", "generate_recommendation_items"]