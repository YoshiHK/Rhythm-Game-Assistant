"""
readability_adjuster.py (Phase 2)

Applies small, deterministic readability adjustments
when narrative text approaches word limits.

This module MUST:
- preserve semantic meaning
- avoid stylistic embellishment
- remain fully deterministic
"""

from __future__ import annotations
from typing import Optional


def _word_count(text: str) -> int:
    """
    Count words in a conservative, deterministic way.
    """
    if not isinstance(text, str):
        return 0
    return len(text.strip().split())


def adjust_readability(
    *,
    text: str,
    max_words: int,
    compact_variant: Optional[str] = None,
) -> str:
    """
    Adjust text readability to fit within max_words.

    Rules:
    1. If text already fits, return as-is.
    2. If text exceeds limit and compact_variant is provided, return it.
    3. Otherwise, truncate conservatively at word boundary.

    This function must not:
    - change tone
    - inject new meaning
    - reorder information
    """
    if not isinstance(text, str):
        return ""

    if max_words <= 0:
        return ""

    if _word_count(text) <= max_words:
        return text

    if isinstance(compact_variant, str) and compact_variant.strip():
        return compact_variant.strip()

    words = text.strip().split()
    truncated = words[:max_words]
    return " ".join(truncated)


__all__ = ["adjust_readability"]