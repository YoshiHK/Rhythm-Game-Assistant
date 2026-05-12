"""
Phase 6 Song Recommendations — Catalog Selector (Deterministic)

Purpose
-------
Provide a deterministic selector implementation to plug into song_rec_coordinator.

This module implements the Softr-era idea:
- compute a target metric for a tier (from coordinator)
- choose top producers near the target
- choose a song near the target, excluding recent recommendations

Design constraints:
- Deterministic: no randomness; stable tie-breaks
- No I/O: operates on an in-memory SongCatalog
- Non-semantic: does not judge gameplay quality; only uses numeric proximity windows
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set, Tuple

# Support both package and flat imports
try:
    from phase6.song_recommendation.song_catalog import SongCatalog, DifficultyRecord
except Exception:
    from song_catalog import SongCatalog, DifficultyRecord


@dataclass(frozen=True)
class SelectorConfig:
    # Match window around target metric
    window: float = 2.0
    # widen steps (deterministic fallback)
    widen_steps: Tuple[float, ...] = (2.0, 4.0, 6.0, 10.0)
    # number of producers to consider (if producer info exists)
    top_producers: int = 5


def _safe_float(x: Any, default: float = 0.0) -> float:
    try:
        return float(x)
    except Exception:
        return default


def _producer_score(
    *,
    producer_avg: Optional[float],
    target_metric: float,
    fallback_mean: Optional[float],
) -> float:
    """
    Deterministic producer closeness score.
    Prefer producer_avg if available; otherwise use fallback_mean.
    """
    if producer_avg is not None:
        return abs(producer_avg - target_metric)
    if fallback_mean is not None:
        return abs(fallback_mean - target_metric)
    return 0.0


def rank_producers_for_target(
    catalog: SongCatalog,
    *,
    tier_id: str,
    target_metric: float,
    window: float,
    top_k: int = 5,
) -> List[str]:
    """
    Return producer_id list ranked by closeness to target.
    Only producers with at least one song in the tier window are considered.

    Deterministic tie-break: (score, producer_id)
    """
    records = catalog.iter_difficulty(tier_id)
    if not records:
        return []

    # Gather per-producer metrics within window
    by_producer: Dict[str, List[float]] = {}
    for dr in records:
        if dr.producer_id is None:
            continue
        if abs(dr.metric - target_metric) > window:
            continue
        by_producer.setdefault(dr.producer_id, []).append(dr.metric)

    if not by_producer:
        return []

    ranked: List[Tuple[float, str]] = []
    for pid, metrics in by_producer.items():
        prod = catalog.get_producer(pid)
        avg = prod.avg_difficulty if prod else None
        mean_metric = sum(metrics) / len(metrics) if metrics else None
        score = _producer_score(producer_avg=avg, target_metric=target_metric, fallback_mean=mean_metric)
        ranked.append((score, pid))

    ranked.sort(key=lambda x: (x[0], x[1]))
    return [pid for _, pid in ranked[:top_k]]


def select_song_for_target(
    catalog: SongCatalog,
    *,
    tier_id: str,
    target_metric: float,
    excluded_song_ids: Set[str],
    config: SelectorConfig = SelectorConfig(),
) -> Optional[Dict[str, Any]]:
    """
    Deterministically select a song dict for a (tier_id, target_metric), respecting exclusions.

    Strategy:
    1) Try producer-ranked whitelist + deterministic_pick_song within window
    2) Fallback: deterministic_pick_song without producer whitelist
    3) Widen window deterministically
    """
    # Try with producer whitelist first (if producers exist)
    for w in config.widen_steps:
        producer_whitelist = rank_producers_for_target(
            catalog,
            tier_id=tier_id,
            target_metric=target_metric,
            window=w,
            top_k=config.top_producers,
        )
        if producer_whitelist:
            chosen = catalog.deterministic_pick_song(
                tier_id=tier_id,
                target_metric=target_metric,
                producer_whitelist=producer_whitelist,
                excluded_song_ids=excluded_song_ids,
                window=w,
            )
            if chosen:
                chosen.setdefault("rationale", {})
                chosen["rationale"].setdefault("why", [])
                chosen["rationale"]["why"].append(f"producer_whitelist={len(producer_whitelist)}")
                chosen["rationale"]["why"].append(f"window={w}")
                return chosen

        # Fallback without producer restriction
        chosen = catalog.deterministic_pick_song(
            tier_id=tier_id,
            target_metric=target_metric,
            producer_whitelist=None,
            excluded_song_ids=excluded_song_ids,
            window=w,
        )
        if chosen:
            chosen.setdefault("rationale", {})
            chosen["rationale"].setdefault("why", [])
            chosen["rationale"]["why"].append("producer_whitelist=none")
            chosen["rationale"]["why"].append(f"window={w}")
            return chosen

    return None


def make_catalog_selector(
    catalog: SongCatalog,
    *,
    config: SelectorConfig = SelectorConfig(),
):
    """
    Return a selector callable compatible with song_rec_coordinator:

        selector(target, excluded_song_ids) -> song dict | None

    The coordinator owns the Target shape; we only consume:
    - target.tier_id
    - target.target_count (used as target_metric proxy)
    """
    def selector(target, excluded_song_ids: Set[str]) -> Optional[Dict[str, Any]]:
        # coordinator target_count is a generalized scalar; treat it as metric target
        target_metric = _safe_float(getattr(target, "target_count", 0), default=0.0)
        tier_id = getattr(target, "tier_id", None)
        if not isinstance(tier_id, str) or not tier_id:
            return None

        return select_song_for_target(
            catalog,
            tier_id=tier_id,
            target_metric=target_metric,
            excluded_song_ids=excluded_song_ids,
            config=config,
        )

    return selector