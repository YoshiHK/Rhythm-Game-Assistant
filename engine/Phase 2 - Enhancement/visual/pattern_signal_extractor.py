"""
pattern_signal_extractor.py (Phase 2)

Stage 2–4.1 helper: Extract detected pattern-signal tags.

This module is intentionally minimal:
- It does NOT infer tags.
- It only standardizes access to detected_tags from payload.

Tag normalization and parity checks belong in Phase 2 candidate/tag layers.
"""

from __future__ import annotations

from typing import Any, Dict, List


def extract_detected_tags(canonical_payload: Dict[str, Any], *, key: str = "detected_tags") -> List[str]:
    """
    Return detected_tags list from payload if present; otherwise [].

    Best-effort:
- Keep only non-empty strings
- Preserve order
    """
    if not isinstance(canonical_payload, dict):
        return []

    tags = canonical_payload.get(key)
    if not isinstance(tags, list):
        return []

    out: List[str] = []
    for t in tags:
        if isinstance(t, str):
            s = t.strip()
            if s:
                out.append(s)
    return out


__all__ = ["extract_detected_tags"]