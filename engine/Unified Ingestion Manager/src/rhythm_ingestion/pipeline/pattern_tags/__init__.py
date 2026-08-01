"""
rhythm_ingestion.pipeline.pattern_tags

Canonical pattern tag taxonomy and semantic helpers.

This module defines the *semantic meaning* of low-level pattern tags
emitted during Phase 2 (visual detection and pattern scanning).

It provides:
- a stable tag taxonomy
- tag -> skill-category mappings
- lightweight aggregation helpers for downstream reasoning

This package MUST NOT:
- detect tags
- modify raw detection logic
- generate tips or narrative
- depend on ingestion or orchestration
"""

from __future__ import annotations

from typing import Dict, List, Iterable
from collections import Counter


# ---------------------------------------------------------------------
# Canonical pattern tag taxonomy
# ---------------------------------------------------------------------

# Tags are grouped by *skill axis*, not by implementation detail.
PATTERN_TAG_CATEGORIES: Dict[str, str] = {
    # Density / stamina
    "stream": "density",
    "burst": "burst",
    "burst.start": "burst",
    "burst.end": "burst",

    # Rhythm / timing
    "irregular_rhythm": "rhythm",
    "polyrhythm": "rhythm",
    "swing": "rhythm",

    # Coordination / control
    "trill_vertical": "coordination",
    "trill_horizontal": "coordination",
    "staircase": "coordination",
    "alternating_lanes": "coordination",

    # Reading / visibility
    "low_visibility": "readability",
    "overlapping_notes": "readability",
    "dense_visuals": "readability",

    # Movement / positioning
    "wide_jump": "movement",
    "lane_cross": "movement",
    "slide_cross": "movement",

    # Holds / traces
    "long_hold": "hold",
    "hold_release_timing": "hold",
    "trace_path": "hold",
    "trace_flick": "hold",

    # Gimmicks / structure
    "fake_end": "gimmick",
    "chart_stop": "gimmick",
    "sudden_speed_change": "gimmick",
}


# ---------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------

def get_tag_category(tag: str) -> str | None:
    """
    Return the semantic category for a given pattern tag.
    """
    return PATTERN_TAG_CATEGORIES.get(tag)


def group_tags_by_category(tags: Iterable[str]) -> Dict[str, List[str]]:
    """
    Group a list of pattern tags into semantic categories.

    Returns:
        { category: [tag1, tag2, ...] }
    """
    grouped: Dict[str, List[str]] = {}
    for tag in tags:
        cat = get_tag_category(tag)
        if cat is None:
            continue
        grouped.setdefault(cat, []).append(tag)
    return grouped


def count_tags_by_category(tags: Iterable[str]) -> Dict[str, int]:
    """
    Count how many tags fall into each semantic category.
    """
    counter: Counter[str] = Counter()
    for tag in tags:
        cat = get_tag_category(tag)
        if cat:
            counter[cat] += 1
    return dict(counter)


def dominant_tag_categories(
    tags: Iterable[str],
    *,
    top_k: int = 2,
) -> List[str]:
    """
    Return the top-K dominant semantic categories based on tag frequency.
    """
    counts = count_tags_by_category(tags)
    if not counts:
        return []
    return [
        cat
        for cat, _ in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
    ][:top_k]


__all__ = [
    "PATTERN_TAG_CATEGORIES",
    "get_tag_category",
    "group_tags_by_category",
    "count_tags_by_category",
    "dominant_tag_categories",
]
