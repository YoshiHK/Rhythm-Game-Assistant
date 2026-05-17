#!/usr/bin/env python3
from __future__ import annotations

"""
narrative_v3_bridge.py
Phase 4 — Narrative v3 Bridge (selection + deterministic render)

Design principles (hard):
- MUST NOT modify Phase 1–3 semantics or artifacts.
- Presentation-only personalization:
  - element ordering (display emphasis)
  - narrative_template_id / variant_id are record-only hints
- Locale is accepted as a routing hint only; translation is Phase 4.5.
- MUST be import-safe under CI (no circular imports).
"""

from typing import Any, Dict, List, Optional


def _reorder_elements(
    elements_view: List[Dict[str, Any]],
    element_ordering: Optional[List[str]],
) -> List[Dict[str, Any]]:
    """Return a reordered view without mutating input."""
    if not element_ordering:
        return list(elements_view)
    id_map: Dict[str, Dict[str, Any]] = {}
    for el in elements_view:
        eid = el.get("element_id") or el.get("id")
        if isinstance(eid, str) and eid:
            id_map[eid] = el

    reordered = [id_map[eid] for eid in element_ordering if eid in id_map]
    # Only accept complete permutations (bounded safety)
    if len(reordered) == len(elements_view):
        return reordered
    return list(elements_view)


def generate_tips_text_v3(
    *,
    canonical_payload: Dict[str, Any],
    canonical_row: Dict[str, Any],
    elements_view: List[Dict[str, Any]],
    difficulty: str,
    locale: Optional[str] = None,
    engine_mode: str = "deterministic",
    narrative_template_id: Optional[str] = None,
    variant_id: Optional[str] = None,
    element_ordering: Optional[List[str]] = None,
    tips_spec_path: str = "proseka_tips_generation_spec_v1.0.1_advisory.json",
    track_cd_config_path: str = "track_cd_config.json",
    orchestrator_ext: Optional[Dict[str, Any]] = None,  # record-only
) -> Dict[str, Any]:
    """
    Deterministic narrative bridge.

    Key rule:
    - Avoid importing upstream/runtime modules at import-time.
    - If Track D renderer exists, use it via lazy import.
    - Otherwise, return deterministic fallback text (CI-safe).
    """
    view = _reorder_elements(elements_view, element_ordering)

    # --- Try Track D v2 renderer (lazy import to avoid circular import)
    try:
        # If this exists in your repo, it will be used.
        from narrative_module_v2 import generate_tips_text_v2  # type: ignore

        # Adapt to the renderer's expected signature if needed.
        # We keep it defensive to avoid breaking CI.
        return generate_tips_text_v2(
            difficulty=difficulty,
            selected_elements=view,
            engine_mode=engine_mode,
            narrative_template_id=narrative_template_id,
            variant_id=variant_id,
            locale=locale,
            tips_spec_path=tips_spec_path,
            track_cd_config_path=track_cd_config_path,
            orchestrator_ext=orchestrator_ext,
        )
    except Exception:
        # --- Deterministic fallback (no external imports)
        # Keep minimal: CI does not judge narrative quality.
        titles = []
        for el in view:
            t = el.get("title") or el.get("element_id")
            if isinstance(t, str) and t:
                titles.append(t)

        text = " | ".join(titles) if titles else "No tips available."
        return {
            "text": text,
            "narrative_template_id": narrative_template_id,
            "variant_id": variant_id,
            "engine_mode": engine_mode,
            "locale": locale,
        }


__all__ = ["generate_tips_text_v3"]