"""
taxonomy_helpers.py (Phase 2)

Lightweight helpers for taxonomy/category handlingLightweight helpers for taxonomy/category handling.
from typing import Iterable, List


def normalize_taxonomy_labels(labels: Iterable[str]) -> List[str]:
    """
    Normalize taxonomy labels for stable comparison.

    Rules:
    - lowercase
    - strip whitespace
    - drop empty values
    - preserve order
    """
    out: List[str] = []
    for x in labels or []:
        if not isinstance(x, str):
            continue
        s = x.strip().lower()
        if s:
            out.append(s)
    return out


__all__ = ["normalize_taxonomy_labels"]

No semantic interpretation is allowed here.
"""

