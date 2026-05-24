"""
Phase 6 Song Recommendations — Catalog Selector (Deterministic)

### Purpose

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

from .song_catalog import SongCatalog, DifficultyRecord  # Phase 6 package-local import

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
    """
    ranked: List[Tuple[str, float]] = []

    for pid in catalog.list_producers():
        records = catalog.get_difficulty_records(
            tier_id=tier_id,
            producer_id=pid,
            min_metric=target_metric - window,
            max_metric=target_metric + window,
        )
        if not records:
            continue

        producer_avg = catalog.get_producer_avg_metric(pid, tier_id)
        fallback_mean = catalog.get_global_mean_metric(tier_id)
        score = _producer_score(
            producer_avg=producer_avg,
            target_metric=target_metric,
            fallback_mean=fallback_mean,
        )
        ranked.append((pid, score))

    ranked.sort(key=lambda x: (x[1], x[0]))  # deterministic tie-break
    return [pid for pid, _ in ranked[:top_k]]


def select_song_for_target(
    catalog: SongCatalog,
    *,
    tier_id: str,
    target_metric: float,
    excluded_song_ids: Set[str],
    config: SelectorConfig = SelectorConfig(),
) -> Optional[Dict[str, Any]]:
    """
    Deterministically select a song dict for a (tier_id, target_metric),
    respecting exclusions.

    Returns a dict with:
      - song_id
      - difficulty
      - metric
      - diagnostics (selection window, widen step, producer rank)
    """
    diagnostics: Dict[str, Any] = {}

    for widen_idx, window in enumerate(config.widen_steps):
        producer_ids = rank_producers_for_target(
            catalog,
            tier_id=tier_id,
            target_metric=target_metric,
            window=window,
            top_k=config.top_producers,
        )
        if not producer_ids:
            continue

        diagnostics["window_used"] = window
        diagnostics["widen_step_index"] = widen_idx

        for producer_rank, pid in enumerate(producer_ids, start=1):
            records: List[DifficultyRecord] = catalog.get_difficulty_records(
                tier_id=tier_id,
                producer_id=pid,
                min_metric=target_metric - window,
                max_metric=target_metric + window,
            )
            if not records:
                continue

            # Deterministic order: closest metric first, stable tie-break by song_id
            records.sort(
                key=lambda r: (abs(_safe_float(r.metric) - target_metric), r.song_id)
            )

            for rec in records:
                if rec.song_id in excluded_song_ids:
                    continue

                diagnostics["producer_rank"] = producer_rank
                diagnostics["selection_reason_codes"] = [
                    "within_window",
                    "producer_proximity",
                ]

                return {
                    "song_id": rec.song_id,
                    "difficulty": rec.difficulty,
                    "level": rec.level,
                    "metric": _safe_float(rec.metric),
                    "diagnostics": diagnostics,
                }

    return None


def make_catalog_selector(
    catalog: SongCatalog,
    *,
    config: SelectorConfig = SelectorConfig(),
):
    """
    Return a selector callable compatible with song_rec_coordinator.

    The returned callable:
    - accepts (tier_id, target_metric, excluded_song_ids)
    - returns (item_dict, diagnostics_dict)
    """

    def _selector(
        *,
        tier_id: str,
        target_metric: float,
        excluded_song_ids: Set[str],
    ) -> Tuple[Optional[Dict[str, Any]], Dict[str, Any]]:
        result = select_song_for_target(
            catalog,
            tier_id=tier_id,
            target_metric=target_metric,
            excluded_song_ids=excluded_song_ids,
            config=config,
        )
        if result is None:
            return None, {}

        # Split item fields and diagnostics cleanly
        item = {k: v for k, v in result.items() if k != "diagnostics"}
        diag = dict(result.get("diagnostics", {}))
        return item, diag

    return _selector