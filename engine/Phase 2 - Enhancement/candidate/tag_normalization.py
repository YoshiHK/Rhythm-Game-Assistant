"""
tag_normalization.py (Phase 2)

Normalizes detected pattern-signal tags before- define taxonomyNormalizes detected pattern-signal tags before candidate inference.
- invent new tags
- reinterpret Phase 1 semantics

It only provides a deterministic normalization surface.
"""

from __future__ import annotations
from typing import Iterable, List


def normalize_detected_tags(tags: Iterable[str]) -> List[str]:
    """
    Normalize detected tags in a best-effort, deterministic way.

    Rules:
    - keep order
    - strip whitespace
    - drop empty values
    - lowercase for matching stability
    """
    out: List[str] = []
    for t in tags or []:
        if not isinstance(t, str):
            continue
        s = t.strip().lower()
        if not s:
            continue
        out.append(s)
    return out


__all__ = ["normalize_detected_tags"]

This module does NOT:
