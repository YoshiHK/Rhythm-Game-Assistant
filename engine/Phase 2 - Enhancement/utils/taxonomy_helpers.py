"""
taxonomy_helpers.py (Phase 2)

Lightweight helpers for taxonomy/category handling.

This module:
- does NOT reinterpret taxonomy semantics
- does NOT invent new categories
- provides deterministic helper utilities only
"""

from __future__ import annotations

from typing import Iterable, List


def normalize_taxonomy_labels(labels: Iterable[str]) -> List[str]:
    """
    Normalize taxonomy labels for stable comparison.

    Current behavior:
    - preserve order
    - strip whitespace
    - drop empty or non-string values
    """
    normalized: List[str] = []

    for label in labels:
        if not isinstance(label, str):
            continue
        s = label.strip()
        if s:
            normalized.append(s)

    return normalized


__all__ = ["normalize_taxonomy_labels"]