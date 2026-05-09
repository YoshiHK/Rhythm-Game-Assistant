from __future__ import annotations
from typing import Any, Dict, List, Optional


def apply_diversity_constraints(
    ranked: List[Dict[str, Any]],
    *,
    target_count: int,
    category_key: str = "category",
    max_per_category: int = 2,
) -> List[Dict[str, Any]]:
    """
    Apply a conservative diversity constraint.

    - If elements contain `category`, cap per-category occurrences.
    - If no category exists, return top-N as-is (no-op).

    Deterministic: preserves ranked order, only skips items.
    """
    if target_count <= 0:
        return []

    # Detect whether category exists anywhere
    has_category = any(isinstance(e, dict) and (category_key in e) for e in ranked)
    if not has_category:
        return ranked[:target_count]

    out: List[Dict[str, Any]] = []
    counts: Dict[str, int] = {}

    for e in ranked:
        if not isinstance(e, dict):
            continue
        cat = e.get(category_key)
        cat_s = str(cat) if cat is not None else ""
        if cat_s:
            if counts.get(cat_s, 0) >= max_per_category:
                continue
            counts[cat_s] = counts.get(cat_s, 0) + 1

        out.append(e)
        if len(out) >= target_count:
            break

    # If diversity skipping prevented filling target, backfill ignoring diversity
    if len(out) < target_count:
        already = {id(x) for x in out}
        for e in ranked:
            if id(e) in already:
                continue
            out.append(e)
            if len(out) >= target_count:
                break

    return out[:target_count]


__all__ = ["apply_diversity_constraints"]