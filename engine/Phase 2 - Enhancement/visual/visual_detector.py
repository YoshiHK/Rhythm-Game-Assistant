"""
visual_detector.py (Phase 2)

Stage 2–4.1 entry wrapper.

This module does NOT re-implement Phase 1 visual logic.
It provides deterministic, additive integration:

- If canonical_payload already includes `sections` and/or `detected_tags`,
  it passes through unchanged.
- If an HTML path is provided, it tries to call Phase 1 visual detector
  (`chart_visual_detector_merged.analyze_chart_html`) to produce outputs.
- If the detector is unavailable or inputs are insufficient, it returns payload unchanged.

No Phase 1 code is modified by this module.
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Tuple


def _try_import_phase1_visual_detector():
    """
    Best-effort import of Phase 1 visual detector.
    We avoid hard-binding to a single package layout.
    """
    # Common layouts: same repo root, or Phase_1_Foundation/visual module path.
    candidates = [
        ("chart_visual_detector_merged", "analyze_chart_html"),
        ("Phase_1_Foundation.visual.chart_visual_detector_merged", "analyze_chart_html"),
        ("visual.chart_visual_detector_merged", "analyze_chart_html"),
    ]
    for mod_name, fn_name in candidates:
        try:
            mod = __import__(mod_name, fromlist=[fn_name])
            fn = getattr(mod, fn_name, None)
            if callable(fn):
                return fn
        except Exception:
            continue
    return None


def run_visual_detection(
    *,
    canonical_payload: Dict[str, Any],
    html_path: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Run Stage 2–4.1 visual detection in an additive way.

    - If html_path is provided and a Phase 1 detector is available:
        call Phase 1 detector and merge `sections`, `detected_tags`, `diagnostics`, `meta` into payload.
    - Otherwise:
        no-op (return payload unchanged).
    """
    if not isinstance(canonical_payload, dict):
        return canonical_payload

    # If Phase 1 already produced outputs, do not overwrite.
    has_sections = isinstance(canonical_payload.get("sections"), list)
    has_tags = isinstance(canonical_payload.get("detected_tags"), list)

    if has_sections and has_tags:
        return canonical_payload

    if not html_path:
        return canonical_payload

    detector = _try_import_phase1_visual_detector()
    if detector is None:
        return canonical_payload

    try:
        result = detector(html_path)
    except Exception:
        return canonical_payload

    if not isinstance(result, dict):
        return canonical_payload

    # Additive merge only: fill missing keys, never overwrite existing.
    for k in ("sections", "detected_tags", "diagnostics", "meta"):
        if k not in canonical_payload and k in result:
            canonical_payload[k] = result[k]

    return canonical_payload


def attach_visual_outputs(
    canonical_payload: Dict[str, Any],
    *,
    html_path_key: str = "html_path",
) -> Dict[str, Any]:
    """
    Convenience wrapper:

    Reads html_path from canonical_payload[html_path_key] (if present),
    runs visual detection, and returns the same dict (additive updates only).
    """
    html_path = canonical_payload.get(html_path_key)
    html_path = html_path if isinstance(html_path, str) and html_path.strip() else None
    return run_visual_detection(canonical_payload=canonical_payload, html_path=html_path)


__all__ = [
    "run_visual_detection",
    "attach_visual_outputs",
]