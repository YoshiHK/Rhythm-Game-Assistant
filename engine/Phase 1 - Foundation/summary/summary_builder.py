# -*- coding: utf-8 -*-
"""
Summary builder for Project Sekai tips pipeline (Step 7).

Consumes:
  - elements_skeleton from severity_detector.infer_severities_for_chart()["elements_skeleton"]
  - selected_elements from Step 5.2 (element selector)

Produces:
  - Per-chart summary block matching the canonical schema from proseka_summary_blocks_canonical.json
"""

from __future__ import annotations
from typing import List, Dict, Any, Tuple
from collections import Counter


def _safe_float(x) -> float:
    """Safely convert to float; return 0.0 on failure."""
    try:
        return float(x)
    except Exception:
        return 0.0


def build_summary_from_elements(
    elements_skeleton: List[Dict[str, Any]],
    selected_elements: List[Dict[str, Any]],
    chart_id: Any = None,
    song_id: Any = None,
) -> Dict[str, Any]:
    """
    Build a canonical per-chart summary from elements_skeleton.

    Parameters
    ----------
    elements_skeleton : list[dict]
        Output of severity_detector.infer_severities_for_chart()["elements_skeleton"].
        Each element should contain at least:
          - "element_id"
          - "element_name" (or "name")
          - "category"
          - "severity"
          - "score"            (0..1 or None)
          - "section_coverage" (0..1 or None)

    selected_elements : list[dict]
        Elements selected into tips (Step 5.2).
        Used to compute dominant_selected_flags.

    chart_id, song_id : optional
        Metadata to include in the summary block.

    Returns
    -------
    dict
        {
          "chart_id": chart_id,
          "song_id": song_id,
          "element_count": int,
          "element_frequency": {element_name: int},
          "severity_distribution": {severity: int},
          "avg_score": float,
          "avg_section_coverage": float,
          "max_score": float,
          "dominant_elements": [element_name, ...],
          "dominant_selected_flags": {element_name: bool},
          # optional extras:
          "top_elements": [...],
        }
    """
    # Handle empty case early.
    if not elements_skeleton:
        return {
            "chart_id": chart_id,
            "song_id": song_id,
            "element_count": 0,
            "element_frequency": {},
            "severity_distribution": {},
            "avg_score": 0.0,
            "avg_section_coverage": 0.0,
            "max_score": 0.0,
            "dominant_elements": [],
            "dominant_selected_flags": {},
            "top_elements": [],
        }

    # ------------------------------------------------------------------
    # 1) Compute dominant_score = score * section_coverage
    # ------------------------------------------------------------------
    scored: List[Tuple[float, Dict[str, Any]]] = []
    for el in elements_skeleton:
        score = _safe_float(el.get("score"))
        coverage = _safe_float(el.get("section_coverage"))
        dominant_score = score * coverage
        scored.append((dominant_score, el))

    # Sort by dominant score descending
    scored.sort(key=lambda x: x[0], reverse=True)

    # For convenience, keep a "top_elements" list (not required by schema)
    TOP_N = 5
    top_elements_raw = scored[:TOP_N]
    top_elements = [
        {
            "element_id": el.get("element_id"),
            "name": el.get("element_name", el.get("name")),
            "category": el.get("category"),
            "severity": el.get("severity"),
            "score": el.get("score"),
            "section_coverage": el.get("section_coverage"),
            "dominant_score": dom,
        }
        for dom, el in top_elements_raw
        if dom > 0.0
    ]

    # ------------------------------------------------------------------
    # 2) Severity distribution
    # ------------------------------------------------------------------
    severity_dist: Dict[str, int] = {}
    for _, el in scored:
        sev = el.get("severity")
        if not sev:
            continue
        severity_dist[sev] = severity_dist.get(sev, 0) + 1

    # ------------------------------------------------------------------
    # 3) Score / coverage statistics
    # ------------------------------------------------------------------
    scores = [
        _safe_float(el.get("score"))
        for _, el in scored
        if el.get("score") is not None
    ]
    coverages = [
        _safe_float(el.get("section_coverage"))
        for _, el in scored
        if el.get("section_coverage") is not None
    ]

    avg_score = sum(scores) / len(scores) if scores else 0.0
    avg_section_coverage = sum(coverages) / len(coverages) if coverages else 0.0

    # dominant score max
    max_score = scored[0][0] if scored else 0.0

    # ------------------------------------------------------------------
    # 4) Element frequency (per element_name)
    # ------------------------------------------------------------------
    element_frequency = Counter(
        el.get("element_name", el.get("name"))
        for _, el in scored
    )

    # ------------------------------------------------------------------
    # 5) Dominant elements and selection flags
    # ------------------------------------------------------------------
    tolerance = 1e-9
    dominant_elements = [
        el.get("element_name", el.get("name"))
        for dom, el in scored
        if abs(dom - max_score) <= tolerance and dom > 0.0
    ]

    selected_names = {
        el.get("element_name", el.get("name"))
        for el in selected_elements
    }

    dominant_selected_flags = {
        name: (name in selected_names)
        for name in dominant_elements
    }

    # ------------------------------------------------------------------
    # 6) Canonical per-chart summary block
    # ------------------------------------------------------------------
    summary: Dict[str, Any] = {
        "chart_id": chart_id,
        "song_id": song_id,
        "element_count": len(elements_skeleton),
        "element_frequency": dict(element_frequency),
        "severity_distribution": severity_dist,
        "avg_score": avg_score,
        "avg_section_coverage": avg_section_coverage,
        "max_score": max_score,
        "dominant_elements": dominant_elements,
        "dominant_selected_flags": dominant_selected_flags,
        # Optional extra for QA:
        "top_elements": top_elements,
    }

    return summary
