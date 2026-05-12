"""
Phase 6 Song Recommendations — Coordinator

Purpose
-------
Coordinate mode="songs" recommendation generation as a Phase 6-owned wiring layer.

Responsibilities:
- Use NormalizedSongRecRequest + resolved GameCapability
- Compute 3-in-a-group targets (AP/FC/Clear logical types) via completion ladder
- Invoke injected selector (catalog-backed) deterministically
- Return items + diagnostics (no persistence here)

Design constraints:
- deterministic
- no I/O
- multi-game safe (no hardcoded tier/label semantics)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Sequence, Set, Tuple

from request_normalizer import NormalizedSongRecRequest
from game_capability_resolver import GameCapability, canonicalize_completion_id, canonicalize_tier_id


@dataclass(frozen=True)
class Target:
    tier_id: str
    completion_id: str
    target_count: int


def _sum_counts(counts: Dict[str, int]) -> int:
    return sum(int(v) for v in counts.values() if isinstance(v, int) and v >= 0)


def _weighted_fraction(counts: Dict[str, int], ladder: Sequence[str]) -> float:
    """
    Generalize 'fractional skill' using ladder positions.

    For a 3-step ladder (clear < fc < ap), weights are 0.0 / 0.5 / 1.0.
    For longer ladders, weights are linearly spaced in [0, 1].

    Returns a scalar in [0, 1] (approx) used to compute targets.
    """
    total = _sum_counts(counts)
    if total <= 0:
        return 0.0

    n = len(ladder)
    if n <= 1:
        return 1.0

    weights: Dict[str, float] = {}
    for i, cid in enumerate(ladder):
        weights[cid] = i / (n - 1)

    score = 0.0
    for cid, cnt in counts.items():
        score += weights.get(cid, 0.0) * float(cnt)

    return score / float(total)


def compute_targets_from_submission(req: NormalizedSongRecRequest, cap: GameCapability) -> Dict[str, Target]:
    """
    Compute three targets for a recommendation set:
    - AP: ladder top (highest quality)
    - FC: ladder middle
    - Clear: ladder bottom (baseline)

    These labels are stable UI types. They map to game-specific ladder positions.
    """
    tiers: List[Tuple[str, Dict[str, int]]] = []

    for t in req.submission.tiers:
        tid = canonicalize_tier_id(cap, t["tier_id"])
        counts_raw = t["counts"]
        canon_counts: Dict[str, int] = {}
        for k, v in counts_raw.items():
            cid = canonicalize_completion_id(cap, k)
            canon_counts[cid] = int(v)
        tiers.append((tid, canon_counts))

    tier_order = [canonicalize_tier_id(cap, x) for x in cap.difficulty_tiers]
    tier_rank = {tid: i for i, tid in enumerate(tier_order)}
    tiers.sort(key=lambda x: tier_rank.get(x[0], -1), reverse=True)

    chosen_tier_id: Optional[str] = None
    chosen_counts: Dict[str, int] = {}
    for tid, cnts in tiers:
        if _sum_counts(cnts) > 0:
            chosen_tier_id = tid
            chosen_counts = cnts
            break

    if not chosen_tier_id:
        chosen_tier_id = tier_order[-1] if tier_order else tiers[0][0]

    ladder = [canonicalize_completion_id(cap, x) for x in cap.completion_ladder]

    tier_total = _sum_counts(chosen_counts)
    frac = _weighted_fraction(chosen_counts, ladder)

    # ladder mapping points
    if len(ladder) == 1:
        low = mid = high = ladder[0]
    elif len(ladder) == 2:
        low, high = ladder[0], ladder[1]
        mid = high
    else:
        low = ladder[0]
        mid = ladder[len(ladder) // 2]
        high = ladder[-1]

    # target policy (generalized from your Softr logic)
    ap_target = int(tier_total * frac) + 1
    fc_target = int(tier_total * min(1.0, frac + 0.5)) + 1
    clear_target = tier_total + 1

    return {
        "AP": Target(tier_id=chosen_tier_id, completion_id=high, target_count=ap_target),
        "FC": Target(tier_id=chosen_tier_id, completion_id=mid, target_count=fc_target),
        "Clear": Target(tier_id=chosen_tier_id, completion_id=low, target_count=clear_target),
    }


def build_exclusion_set(req: NormalizedSongRecRequest) -> Set[str]:
    """Exclude by song_id only (multi-locale safe)."""
    out: Set[str] = set()
    for r in req.recent_recommendations:
        if r.song_id:
            out.add(r.song_id)
    return out


# Injected selector signature (catalog-backed)
# selector(Target, excluded_song_ids) -> song dict (or None)
SongSelector = Callable[[Target, Set[str]], Optional[Dict[str, Any]]]


def generate_recommendation_items(
    req: NormalizedSongRecRequest,
    cap: GameCapability,
    *,
    selector: SongSelector,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Generate up to 3 items (AP/FC/Clear) using injected selector.
    Determinism must be enforced by selector implementation (tie-break rules).
    """
    excluded = build_exclusion_set(req)
    targets = compute_targets_from_submission(req, cap)

    items: List[Dict[str, Any]] = []
    diagnostics: Dict[str, Any] = {
        "game_id": req.game_id,
        "excluded_count": len(excluded),
        "targets": {
            k: {"tier_id": v.tier_id, "completion_id": v.completion_id, "target_count": v.target_count}
            for k, v in targets.items()
        },
    }

    for rec_type in ("AP", "FC", "Clear"):
        chosen = selector(targets[rec_type], excluded)
        if not chosen:
            continue

        sid = chosen.get("song_id")
        if isinstance(sid, str) and sid:
            excluded.add(sid)

        chosen["recommendation_type"] = rec_type
        items.append(chosen)

    diagnostics["generated_count"] = len(items)
    return items, diagnostics