# -*- coding: utf-8 -*-
"""
Severity + coverage inference stub for Project Sekai tips pipeline.

Connects:
  - SectionMetrics & automatic_inference_framework from proseka_severity_rules.py
  - RULES registry from rules.element_rules (severity_hooks, metric_keys)
  - scoring scheme and severity ordering from proseka_severity_rules.py

Produces:
  - canonical_severities : {canonical_id -> severity}
  - element_severities   : {element_id -> severity or None}
  - elements_skeleton    : list[dict] with severity, score, section_coverage per element
"""

from __future__ import annotations
from typing import List, Dict, Any, Optional

# From your severity model
from proseka_severity_rules import (
    SectionMetrics,
    automatic_inference_framework,
    SEVERITY_INDEX,
    SCORE_TO_SEVERITY,
    map_score_to_severity,
    severity_ge,
    Severity,
)

# From your element registry & helpers
from rules import RULES
from rules.utils import get_jp_name_map


# ----------------------------------------------------------------------
# Internal helpers
# ----------------------------------------------------------------------

def _max_severity(severities: List[Optional[Severity]]) -> Optional[Severity]:
    """Return the strongest severity label using SEVERITY_INDEX.
    Example: ["slight", "moderate", "dense"] -> "dense".
    """
    best_label: Optional[Severity] = None
    best_score: int = -1

    for s in severities:
        if not s:
            continue
        if s not in SEVERITY_INDEX:
            continue
        score = SEVERITY_INDEX[s]
        if score > best_score:
            best_score = score
            best_label = s

    return best_label


def severity_to_score(severity: Optional[Severity]) -> Optional[float]:
    """Map a severity label back to a representative numeric score in [0, 1].

    Strategy:
      - Find the (lo, hi) for which SCORE_TO_SEVERITY has this severity.
      - Return the midpoint (lo + hi) / 2.
      - If severity is None, return None.

    This is a natural inverse of map_score_to_severity().
    """
    if severity is None:
        return None

    for (lo, hi), sev in SCORE_TO_SEVERITY:
        if sev == severity:
            return (lo + hi) / 2.0

    # Fallback: approximate via normalized SEVERITY_INDEX
    if severity in SEVERITY_INDEX:
        idx = SEVERITY_INDEX[severity]
        max_idx = max(SEVERITY_INDEX.values()) or 1
        return idx / max_idx

    return None


# ----------------------------------------------------------------------
# 1. Canonical severity inference
# ----------------------------------------------------------------------

def infer_canonical_from_sections_raw(
    sections: List[SectionMetrics],
) -> Dict[str, Any]:
    """Thin wrapper around automatic_inference_framework(sections).

    Returns
    -------
    dict
        {
          "per_section": [ {canonical_id: severity, ...}, ... ],
          "aggregated": {canonical_id: severity, ...},
        }
    """
    if not sections:
        return {"per_section": [], "aggregated": {}}

    framework_result: Dict[str, Any] = automatic_inference_framework(sections)
    per_section = framework_result.get("per_section", []) or []
    aggregated = framework_result.get("aggregated", {}) or {}
    return {"per_section": per_section, "aggregated": aggregated}


def infer_canonical_severities_from_sections(
    sections: List[SectionMetrics],
) -> Dict[str, Severity]:
    """Convenience wrapper returning only aggregated canonical severities."""
    raw = infer_canonical_from_sections_raw(sections)
    aggregated = raw["aggregated"]

    canonical_severities: Dict[str, Severity] = {}
    for key, value in aggregated.items():
        if isinstance(value, str):
            canonical_severities[key] = value  # type: ignore[assignment]

    return canonical_severities


# ----------------------------------------------------------------------
# 2. Canonical -> element severities via severity_hooks
# ----------------------------------------------------------------------

def infer_element_severities_from_canonical(
    canonical_severities: Dict[str, Severity],
    rules: Dict[str, Dict[str, Any]] = RULES,
) -> Dict[str, Optional[Severity]]:
    """Derive per-element severity using RULES[element_id]["severity_hooks"]."""
    element_severities: Dict[str, Optional[Severity]] = {}

    for element_id, rule in rules.items():
        hooks = rule.get("severity_hooks", []) or []
        if not hooks:
            element_severities[element_id] = None
            continue

        hook_severities: List[Optional[Severity]] = [
            canonical_severities.get(hook) for hook in hooks
        ]
        best = _max_severity(hook_severities)
        element_severities[element_id] = best

    return element_severities


# ----------------------------------------------------------------------
# 3. Section coverage computation
# ----------------------------------------------------------------------

def compute_section_coverage(
    per_section: List[Dict[str, Severity]],
    rules: Dict[str, Dict[str, Any]] = RULES,
    coverage_threshold: Severity = "moderate",
) -> Dict[str, float]:
    """Compute section coverage for each element.

    coverage(E) = (#sections where any hook severity >= coverage_threshold)
                  / total_sections
    """
    total_sections = len(per_section)
    if total_sections == 0:
        return {element_id: 0.0 for element_id in rules.keys()}

    coverage: Dict[str, float] = {}

    for element_id, rule in rules.items():
        hooks = rule.get("severity_hooks", []) or []
        if not hooks:
            coverage[element_id] = 0.0
            continue

        covered_sections = 0

        for sev_map in per_section:
            section_has_element = False
            for hook in hooks:
                sev = sev_map.get(hook)
                if sev and severity_ge(sev, coverage_threshold):
                    section_has_element = True
                    break
            if section_has_element:
                covered_sections += 1

        coverage[element_id] = covered_sections / float(total_sections)

    return coverage


# ----------------------------------------------------------------------
# 4. Build elements[] skeleton with severity, score, coverage
# ----------------------------------------------------------------------

def build_elements_skeleton(
    element_severities: Dict[str, Optional[Severity]],
    section_coverages: Dict[str, float],
    rules: Dict[str, Dict[str, Any]] = RULES,
) -> List[Dict[str, Any]]:
    """Convert element_severities and section_coverages into elements[]."""
    jp_names = get_jp_name_map()

    elements: List[Dict[str, Any]] = []
    for element_id, severity in element_severities.items():
        rule = rules.get(element_id, {})
        jp_name = jp_names.get(element_id, element_id)
        score = severity_to_score(severity)
        coverage = section_coverages.get(element_id, 0.0)

        elements.append({
            "element_id": element_id,
            "element_name": jp_name,
            "category": rule.get("category"),

            "severity": severity,
            "score": score,
            "section_coverage": coverage,

            "severity_hooks": rule.get("severity_hooks", []),
            "tag_candidates": rule.get("tag_candidates", []),

            # Step 5.3 will fill these:
            "is_chart_defining": None,
            "guidance": {
                "difficulty_causes": "",
                "chart_breakdown": "",
                "primary_focus": "",
                "secondary_focus": "",
                "strategy": "",
                "target_section": "",
            },
        })

    return elements


# ----------------------------------------------------------------------
# 5. High-level convenience function
# ----------------------------------------------------------------------

def infer_severities_for_chart(
    sections: List[SectionMetrics],
    rules: Dict[str, Dict[str, Any]] = RULES,
    coverage_threshold: Severity = "moderate",
) -> Dict[str, Any]:
    """High-level entry point for severity + coverage + scoring.

    Returns
    -------
    dict
        {
          "canonical_severities": {canonical_id: severity},
          "per_section":          [ {canonical_id: severity}, ... ],
          "element_severities":   {element_id: severity or None},
          "section_coverages":    {element_id: coverage_float},
          "elements_skeleton":    [ ... ]
        }
    """
    raw = infer_canonical_from_sections_raw(sections)
    canonical_sev = {
        k: v for k, v in raw["aggregated"].items() if isinstance(v, str)
    }
    per_section = raw["per_section"]

    element_sev = infer_element_severities_from_canonical(canonical_sev, rules)
    section_coverages = compute_section_coverage(
        per_section=per_section,
        rules=rules,
        coverage_threshold=coverage_threshold,
    )
    elements = build_elements_skeleton(
        element_severities=element_sev,
        section_coverages=section_coverages,
        rules=rules,
    )

    return {
        "canonical_severities": canonical_sev,
        "per_section": per_section,
        "element_severities": element_sev,
        "section_coverages": section_coverages,
        "elements_skeleton": elements,
    }
