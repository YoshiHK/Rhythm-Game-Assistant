"""
tag_normalization.py (Phase 2)

Normalizes detected pattern-signal tags before candidate inference.

This module:
- does NOT invent new tags
- does NOT reinterpret Phase 1 semantics
- only provides a deterministic normalization surface
"""

from __future__ import annotations

from typing import Iterable, List


def normalize_detected_tags(tags: Iterable[str]) -> List[str]:
    """
    Normalize detected tags in a best-effort, deterministic way.

    This function:
    - preserves original order
    - ignores non-string values
    - strips leading/trailing whitespace
    - drops empty strings
    """
    normalized: List[str] = []

    for tag in tags:
        if not isinstance(tag, str):
            continue
        t = tag.strip()
        if t:
            normalized.append(t)

    return normalized


__all__ = ["normalize_detected_tags"]