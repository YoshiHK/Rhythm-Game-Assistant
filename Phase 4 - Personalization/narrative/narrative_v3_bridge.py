#!/usr/bin/env python3
"""
narrative_v3_bridge.py

Phase 4 — Narrative v3 Bridge (selection + deterministic render)

Design principles (hard):
- MUST NOT modify Phase 1–3 semantics or artifacts.
- MUST reuse Phase 2 Track D renderer (narrative_module_v2.generate_tips_text_v2)
  as the single source of textual truth.
- Personalization is presentation-only:
  - element ordering (display emphasis)
  - template_id / variant_id selection (record-only metadata; content is not generated here)
- Locale is accepted as a routing hint only; translation is Phase 4.5.
- Deterministic fallback must always exist.

Orchestrator Extension wiring:
- Accepts an optional `orchestrator_ext` context dict (record-only).
- Does NOT call orchestrator extension logic and does NOT schedule work.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from narrative_module_v2 import generate_tips_text_v2


def _reorder_elements(
    selected_elements: List[Dict[str, Any]],
    element_ordering: Optional[List[str]],
) -> List[Dict[str, Any]]:
    """
    Return a reordered view of elements without mutating input.

    Ordering is applied by element_id (or id fallback).
    Unknown IDs are ignored; remaining elements keep original order.
    """
    if not element_ordering:
        return list(selected_elements)

    by_id: Dict[str, Dict[str, Any]] = {}
    for e in selected_elements:
        eid = str(e.get("element_id") or e.get("id") or "")
        if eid:
            by_id[eid] = e

    ordered: List[Dict[str, Any]] = []
    seen = set()

    for eid in element_ordering:
        eid = str(eid)
        if eid in by_id and eid not in seen:
            ordered.append(by_id[eid])
            seen.add(eid)

    for e in selected_elements:
        eid = str(e.get("element_id") or e.get("id") or "")
        if eid and eid in seen:
            continue
        ordered.append(e)

    return ordered


def generate_tips_text_v3(
    difficulty: str,
    selected_elements: List[Dict[str, Any]],
    *,
    engine_mode: str = "deterministic",
    narrative_template_id: Optional[str] = None,
    variant_id: Optional[str] = None,
    element_ordering: Optional[List[str]] = None,
    locale: Optional[str] = None,
    tips_spec_path: str = "proseka_tips_generation_spec_v1.0.1_advisory.json",
    track_cd_config_path: str = "track_cd_config.json",
    orchestrator_ext: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Generate tips text with Phase 4 personalization support.

    Returns:
      {
        "tips_text": str,
        "render_metadata": {
            "engine_mode": "...",
            "locale": "...",
            "element_ordering_applied": bool,
            "narrative_template_id": str|None,
            "variant_id": str|None,
            "orchestrator_ext": {...}  # optional, record-only
        }
      }

    Behavior:
    - Deterministic mode ignores ordering/template/variant for text generation.
    - Personalized mode applies element ordering ONLY, then calls v2 renderer.
    - Template/variant are recorded for explainability and registry alignment only.
    - Any error falls back to deterministic ordering and reruns v2 renderer.
    """

    elements_view = list(selected_elements)
    ordering_applied = False

    if engine_mode == "personalized" and element_ordering:
        elements_view = _reorder_elements(selected_elements, element_ordering)
        ordering_applied = True

    try:
        tips_text = generate_tips_text_v2(
            difficulty=difficulty,
            selected_elements=elements_view,
            tips_spec_path=tips_spec_path,
            track_cd_config_path=track_cd_config_path,
        )
    except Exception:
        tips_text = generate_tips_text_v2(
            difficulty=difficulty,
            selected_elements=list(selected_elements),
            tips_spec_path=tips_spec_path,
            track_cd_config_path=track_cd_config_path,
        )
        ordering_applied = False

    render_metadata: Dict[str, Any] = {
        "engine_mode": engine_mode,
        "locale": locale,
        "element_ordering_applied": ordering_applied,
        "narrative_template_id": narrative_template_id if engine_mode == "personalized" else None,
        "variant_id": variant_id if engine_mode == "personalized" else None,
    }

    if orchestrator_ext is not None:
        render_metadata["orchestrator_ext"] = orchestrator_ext  # record-only

    return {"tips_text": tips_text, "render_metadata": render_metadata}


__all__ = ["generate_tips_text_v3"]