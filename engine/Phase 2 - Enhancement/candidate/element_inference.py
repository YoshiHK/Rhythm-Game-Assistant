"""
element_inference.py (Phase 2)

Infer element candidates from normalized tags and
a resolved tips training mapping.

This module:
- mirrors Phase 1 semantics
- but produces Phase 2 canonical candidate objects
"""

from __future__ import annotations
from typing import Dict, Any, List

from .tag_normalization import normalize_detected_tags


def infer_element_candidates(
    *,
    detected_tags: List[str],
    training_mapping: Dict[str, Any],
    min_tag_hits: int = 1,
) -> List[Dict[str, Any]]:
    """
    Infer element candidates.

    Output objects MUST conform to:
    - element_candidate.interface.md
    - element_candidate.schema.json
    """
    norm_tags = set(normalize_detected_tags(detected_tags))
    if not norm_tags or not isinstance(training_mapping, dict):
        return []

    out: List[Dict[str, Any]] = []

    for element_name, spec in training_mapping.items():
        if not isinstance(element_name, str) or not isinstance(spec, dict):
            continue

        tags = spec.get("tags", [])
        training_items = spec.get("training_items", [])

        if not isinstance(tags, list):
            continue

        matched = [t for t in tags if isinstance(t, str) and t.lower() in norm_tags]
        hit_count = len(matched)

        if hit_count < min_tag_hits:
            continue

        out.append({
            "element_name": element_name,
            "matched_tags": matched,
            "training_items": list(training_items) if isinstance(training_items, list) else [],
            "tag_hit_count": hit_count,
        })

    return out


__all__ = ["infer_element_candidates"]