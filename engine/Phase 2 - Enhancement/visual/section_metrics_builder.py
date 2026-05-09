"""
section_metrics_builder.py (Phase 2)

Stage 2–4.1 helper: Extract SectionMetrics from a canonical payload.

This module is intentionally minimal:
- It does NOT compute SectionMetrics.
- It only standardizes how sections are accessed and validated at a basic level.

Downstream phases can rely on this accessor without importing Phase 1 modules.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


def extract_sections(canonical_payload: Dict[str, Any], *, key: str = "sections") -> List[Dict[str, Any]]:
    """
    Return sections list from payload if present; otherwise [].

    This is a safe accessor (best-effort). It does not enforce schema here.
    Schema enforcement belongs to Phase 2 CI / schemas.
    """
    if not isinstance(canonical_payload, dict):
        return []

    sections = canonical_payload.get(key)
    if not isinstance(sections, list):
        return []

    # Keep only dict-like entries (best-effort).
    out: List[Dict[str, Any]] = []
    for s in sections:
        if isinstance(s, dict):
            out.append(s)
    return out


__all__ = ["extract_sections"]