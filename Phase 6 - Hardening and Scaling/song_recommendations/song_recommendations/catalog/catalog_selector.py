from __future__ import annotations

"""
Phase 6 Song Recommendations — Catalog Selector (Deterministic, CI-safe)

Purpose:
- Provide a deterministic selector callable for song_rec_coordinator.

Design constraints:
- Deterministic: no randomness; stable tie-breaks
- No I/O: operates on an in-memory SongCatalog
- Non-semantic: uses numeric proximity + deterministic widening only
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set, Tuple

from .song_catalog import SongCatalog, DifficultyRecord


@dataclass(frozen=True)
class SelectorConfig:
    # Base match window around target metric
    window: float = 2.0
    # Deterministic widen steps (applied in-order; includes base 0 as first attempt)
    widen_steps: Tuple[float, ...] = (0.0, 2.0, 4.0, 6.0, 10.0)
    # number of producers to consider (if producer info exists)
    top_producers: int = 5


def _safe_float(x: Any, default: float = 0.0) -> float:
    try:
        return float(x)
    except Exception:
        return default


def _row_metric(row: Dict[str, Any]) -> float:
    return _safe_float(row.get("metric") if isinstance(row, dict) else 0.0, 0.0)


def _row_song_id(row: Dict[str, Any]) -> str:
    return str(row.get("song_id") or "")


def _row_producer_id(row: Dict[str, Any]) -> str:
    return str(row.get("producer_id") or "")


def rank_producers_for_target(
    catalog: SongCatalog,
    *,
    tier_id: str,
    target_metric: float,
    window: float,
    top_k: int = 5,
) -> List[str]:
    """
    Return producer_id list ranked by closeness to target (deterministic).

    Only producers with at least one song in the tier window are considered.
    If producer_id is missing, it is treated as empty string and still deterministic.
    """
    tier_id = str(tier_id)
    rows = [r for r in (catalog.rows or []) if isinstance(r, dict) and r.get("tier_id") == tier_id]

    # Collect producer -> best closeness among its songs in window
    best: Dict[str, float] = {}
    for r in rows:
        m = _row_metric(r)
        if abs(m - target_metric) <= window:
            pid = _row_producer_id(r)
            closeness = abs(m - target_metric)
            if pid not in best or closeness < best[pid]:
                best[pid] = closeness

    ranked = sorted(best.items(), key=lambda kv: (kv[1], kv[0]))
    return [pid for pid, _ in ranked[: max(0, int(top_k))]]


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

    Algorithm (CI-safe):
    - filter to tier_id
    - try windows in widen_steps order (deterministic)
    - within a window: prefer nearest metric, stable tie-break by producer_id then song_id
    """
    tier_id = str(tier_id)
    rows = [
        r for r in (catalog.rows or [])
        if isinstance(r, dict)
        and r.get("tier_id") == tier_id
        and _row_song_id(r) not in excluded_song_ids
    ]

    if not rows:
        return None

    base = _safe_float(target_metric, 0.0)
    base_window = _safe_float(config.window, 2.0)

    # deterministic widen sequence
    for widen in config.widen_steps:
        w = base_window + _safe_float(widen, 0.0)
        candidates = [r for r in rows if abs(_row_metric(r) - base) <= w]
        if not candidates:
            continue

        candidates.sort(key=lambda r: (abs(_row_metric(r) - base), _row_producer_id(r), _row_song_id(r)))
        return dict(candidates[0])

    # If still none, return the globally nearest in-tier as deterministic fallback
    rows.sort(key=lambda r: (abs(_row_metric(r) - base), _row_producer_id(r), _row_song_id(r)))
    return dict(rows[0]) if rows else None


def make_catalog_selector(
    catalog: SongCatalog,
    *,
    config: SelectorConfig = SelectorConfig(),
):
    """
    Return a selector callable compatible with song_rec_coordinator:

        selector(target, excluded_song_ids) -> Optional[Dict[str, Any]]

    where target has fields:
      - tier_id
      - completion_id (ignored here)
      - target_count (ignored here)

    The target_metric is derived deterministically:
      - if target has attribute `target_metric`, use it
      - else use 0.0 as baseline (still deterministic)
    """
    def selector(target: Any, excluded_song_ids: Set[str]) -> Optional[Dict[str, Any]]:
        tier_id = str(getattr(target, "tier_id", "") or "")
        if not tier_id:
            return None

        # Deterministic: use provided target_metric if exists, else 0.0
        tm = getattr(target, "target_metric", None)
        target_metric = _safe_float(tm, 0.0)

        return select_song_for_target(
            catalog,
            tier_id=tier_id,
            target_metric=target_metric,
            excluded_song_ids=set(excluded_song_ids or set()),
            config=config,
        )

    return selector


__all__ = [
    "SelectorConfig",
    "rank_producers_for_target",
    "select_song_for_target",
    "make_catalog_selector",
]