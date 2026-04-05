# -*- coding: utf-8 -*-
"""
proseka_severity_rules.py

Portable rule module for Project SEKAI chart element severity.

Contains:
- Global severity semantics
- Threshold tables by element category
- Cross-element escalation rule
- Automatic severity inference framework (metric-driven)

This module is intentionally chart-format-agnostic: you feed SectionMetrics
computed from your parser.
"""

from __future__ import annotations
import json
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Literal, Any

# ----------------------------------------------------------------------
# Severity scale
# ----------------------------------------------------------------------

Severity = Literal["slight", "light", "mild", "moderate", "dense", "complex", "demanding"]

SEVERITY_ORDER: List[Severity] = [
    "slight",
    "light",
    "mild",
    "moderate",
    "dense",
    "complex",
    "demanding",
]

SEVERITY_INDEX: Dict[Severity, int] = {s: i for i, s in enumerate(SEVERITY_ORDER)}

GLOBAL_SEVERITY_SEMANTICS: Dict[Severity, str] = {
    "slight": "Element is incidental; little impact on success.",
    "light": "Element is noticeable but forgiving; errors are usually recoverable.",
    "mild": "Element is recurring but predictable; manageable with focus.",
    "moderate": "Element is central to a section; requires deliberate execution.",
    "dense": "Element is frequent or sustained; errors can cascade.",
    "complex": "Multiple difficulty vectors interact (e.g., speed + reading + motion).",
    "demanding": "Element is a primary failure point; dominates the chart's challenge.",
}

SCORE_TO_SEVERITY: List[Tuple[Tuple[float, float], Severity]] = [
    ((0.00, 0.15), "slight"),
    ((0.16, 0.30), "light"),
    ((0.31, 0.45), "mild"),
    ((0.46, 0.60), "moderate"),
    ((0.61, 0.75), "dense"),
    ((0.76, 0.90), "complex"),
    ((0.91, 1.00), "demanding"),
]


def severity_ge(a: Severity, b: Severity) -> bool:
    """Return True if severity a is greater than or equal to b."""
    return SEVERITY_INDEX[a] >= SEVERITY_INDEX[b]


def clamp01(x: float) -> float:
    if x < 0.0:
        return 0.0
    if x > 1.0:
        return 1.0
    return x


def map_score_to_severity(score: float) -> Severity:
    """Map a continuous score in [0,1] to a discrete severity label."""
    s = clamp01(score)
    for (lo, hi), sev in SCORE_TO_SEVERITY:
        if lo <= s <= hi:
            return sev
    return "demanding"


def bump_severity(sev: Severity, steps: int = 1) -> Severity:
    """Bump severity up by `steps` (capped at 'demanding')."""
    idx = min(SEVERITY_INDEX[sev] + steps, len(SEVERITY_ORDER) - 1)
    return SEVERITY_ORDER[idx]


# ----------------------------------------------------------------------
# SectionMetrics dataclass
# ----------------------------------------------------------------------

@dataclass
class SectionMetrics:
    """Metrics computed per section (or whole chart)."""
    duration_sec: float
    bpm: float
    npb: float
    nps: float
    avg_npb_chart: float
    avg_nps_chart: float
    peak_npb_chart: float
    peak_nps_chart: float
    rest_ratio: float
    hold_coverage: float = 0.0
    notes_during_hold_ratio: float = 0.0
    slide_cross_lane_rate: float = 0.0
    trace_flick_count: int = 0
    flick_density: float = 0.0
    overlap_ratio: float = 0.0
    lane_cross_rate: float = 0.0
    spacing_variance: float = 0.0
    bpm_delta_ratio: float = 0.0
    bpm_shift_count: int = 0
    chart_stop_count: int = 0
    fake_end_flag: bool = False


# ----------------------------------------------------------------------
# Threshold tables (aligned with Tips Generation Guides)
# ----------------------------------------------------------------------

FLOW_THRESHOLDS = {
    # stream-like sustained flow; CSV: npb ≥ ~1.5× avg for ≥ 2–3 measures
    "dense":    {"npb_mult_min": 1.5, "min_duration_sec": 5.0},
    "moderate": {"npb_mult_max": 1.4, "min_duration_sec": 4.0},
    "mild":     {"npb_mult_max": 1.3, "min_duration_sec": 2.0},
    "light":    {"npb_mult_max": 1.2, "max_duration_sec": 3.0},
    "slight":   {"npb_mult_max": 1.1, "max_duration_sec": 2.0},
}

BURST_THRESHOLDS = {
    # short high-density spikes
    "moderate": {"peak_mult_min": 2.0},
    "mild":     {"peak_mult_max": 1.8},
    "light":    {"peak_mult_max": 1.5},
}

BPM_SHIFT_THRESHOLDS = {
    "slight":   {"delta_ratio_max": 0.10},
    "light":    {"delta_ratio_max": 0.15},
    "mild":     {"delta_ratio_max": 0.20},
    "moderate": {"delta_ratio_min": 0.25},
}

LOW_BPM_HIGH_DENSITY_THRESHOLDS = {
    "mild":     {"bpm_max": 120, "npb_mult_min": 1.00},
    "moderate": {"bpm_max": 110, "npb_mult_min": 1.20},
    "dense":    {"bpm_max": 100, "npb_mult_min": 1.40},
}

HOLD_INTERFERENCE_THRESHOLDS = {
    "light":    {"hold_cov_max": 0.20},
    "moderate": {"hold_cov_min": 0.30},
    "dense":    {"notes_during_hold_min": 0.35},
}

READABILITY_THRESHOLDS = {
    "light":    {"overlap_min": 0.15},
    "mild":     {"overlap_min": 0.25},
    "moderate": {"lane_cross_min": 0.25},
    "dense":    {"overlap_min": 0.45},
}

DURATION_THRESHOLDS = {
    "slight":   {"duration_ratio_min": 1.10},
    "light":    {"duration_ratio_min": 1.20, "rest_ratio_min": 0.30},
    "moderate": {"rest_ratio_max": 0.25},
    "dense":    {"rest_ratio_max": 0.15},
}


# ----------------------------------------------------------------------
# Automatic inference functions (canonical severities)
# ----------------------------------------------------------------------

def infer_stream_severity(m: SectionMetrics) -> Severity:
    mult = (m.npb / m.avg_npb_chart) if m.avg_npb_chart > 0 else 1.0

    if mult >= FLOW_THRESHOLDS["dense"]["npb_mult_min"] \
       and m.duration_sec >= FLOW_THRESHOLDS["dense"]["min_duration_sec"]:
        return "dense"

    if mult <= FLOW_THRESHOLDS["slight"]["npb_mult_max"] \
       and m.duration_sec <= FLOW_THRESHOLDS["slight"]["max_duration_sec"]:
        return "slight"

    if mult <= FLOW_THRESHOLDS["light"]["npb_mult_max"] \
       and m.duration_sec <= FLOW_THRESHOLDS["light"]["max_duration_sec"]:
        return "light"

    if mult <= FLOW_THRESHOLDS["mild"]["npb_mult_max"] \
       and m.duration_sec >= FLOW_THRESHOLDS["mild"]["min_duration_sec"]:
        return "mild"

    if mult <= FLOW_THRESHOLDS["moderate"]["npb_mult_max"] \
       and m.duration_sec >= FLOW_THRESHOLDS["moderate"]["min_duration_sec"]:
        return "moderate"

    return "moderate"


def infer_burst_severity(m: SectionMetrics) -> Severity:
    peak_mult = (m.peak_npb_chart / m.avg_npb_chart) if m.avg_npb_chart > 0 else 1.0

    if peak_mult >= BURST_THRESHOLDS["moderate"]["peak_mult_min"]:
        # differentiate moderate vs dense by spike extremity
        if m.peak_npb_chart < m.avg_npb_chart * 3.0:
            return "moderate"
        else:
            return "dense"

    if peak_mult <= BURST_THRESHOLDS["light"]["peak_mult_max"]:
        return "light"

    if peak_mult <= BURST_THRESHOLDS["mild"]["peak_mult_max"]:
        return "mild"

    return "moderate"


def infer_bpm_shift_severity(m: SectionMetrics) -> Severity:
    dr = abs(m.bpm_delta_ratio)

    if dr >= BPM_SHIFT_THRESHOLDS["moderate"]["delta_ratio_min"] or m.bpm_shift_count >= 2:
        return "moderate" if m.bpm_shift_count < 3 else "dense"

    if dr <= BPM_SHIFT_THRESHOLDS["slight"]["delta_ratio_max"]:
        return "slight"

    if dr <= BPM_SHIFT_THRESHOLDS["light"]["delta_ratio_max"]:
        return "light"

    if dr <= BPM_SHIFT_THRESHOLDS["mild"]["delta_ratio_max"]:
        return "mild"

    return "moderate"


def infer_low_bpm_high_density_severity(m: SectionMetrics) -> Optional[Severity]:
    mult = (m.npb / m.avg_npb_chart) if m.avg_npb_chart > 0 else 1.0

    if m.bpm < LOW_BPM_HIGH_DENSITY_THRESHOLDS["dense"]["bpm_max"] \
       and mult >= LOW_BPM_HIGH_DENSITY_THRESHOLDS["dense"]["npb_mult_min"]:
        return "dense"

    if m.bpm < LOW_BPM_HIGH_DENSITY_THRESHOLDS["moderate"]["bpm_max"] \
       and mult >= LOW_BPM_HIGH_DENSITY_THRESHOLDS["moderate"]["npb_mult_min"]:
        return "moderate"

    if m.bpm < LOW_BPM_HIGH_DENSITY_THRESHOLDS["mild"]["bpm_max"] \
       and mult >= LOW_BPM_HIGH_DENSITY_THRESHOLDS["mild"]["npb_mult_min"]:
        return "mild"

    return None


def infer_hold_interference_severity(m: SectionMetrics) -> Optional[Severity]:
    if m.hold_coverage <= HOLD_INTERFERENCE_THRESHOLDS["light"]["hold_cov_max"] \
       and m.notes_during_hold_ratio < 0.20:
        return "light" if m.hold_coverage > 0 else None

    if m.hold_coverage >= HOLD_INTERFERENCE_THRESHOLDS["moderate"]["hold_cov_min"]:
        sev: Severity = "moderate"
        if m.notes_during_hold_ratio >= HOLD_INTERFERENCE_THRESHOLDS["dense"]["notes_during_hold_min"]:
            sev = "dense"
        if m.slide_cross_lane_rate >= 0.35:
            sev = bump_severity(sev, 1)
        return sev

    return None


def infer_trace_flick_severity(m: SectionMetrics) -> Optional[Severity]:
    if m.trace_flick_count <= 0:
        return None

    if m.trace_flick_count >= 6 or m.flick_density >= 2.0:
        return "complex"

    if m.trace_flick_count >= 3 or m.flick_density >= 1.0:
        return "moderate"

    return "mild"


def infer_readability_severity(m: SectionMetrics) -> Optional[Severity]:
    if m.overlap_ratio < READABILITY_THRESHOLDS["light"]["overlap_min"] \
       and m.lane_cross_rate < READABILITY_THRESHOLDS["moderate"]["lane_cross_min"]:
        return None

    if m.overlap_ratio >= READABILITY_THRESHOLDS["dense"]["overlap_min"]:
        return "dense"

    if m.lane_cross_rate >= READABILITY_THRESHOLDS["moderate"]["lane_cross_min"]:
        return "moderate"

    if m.overlap_ratio >= READABILITY_THRESHOLDS["mild"]["overlap_min"]:
        return "mild"

    return "light"


def infer_temporal_disruption_severity(m: SectionMetrics) -> Optional[Severity]:
    if m.chart_stop_count <= 0 and not m.fake_end_flag:
        return None

    sev: Severity = "light" if m.chart_stop_count == 1 else "moderate"
    if m.chart_stop_count >= 2:
        sev = "dense"

    if m.fake_end_flag and SEVERITY_INDEX[sev] < SEVERITY_INDEX["complex"]:
        sev = "complex"

    return sev


# ----------------------------------------------------------------------
# Cross-element escalation rule
# ----------------------------------------------------------------------

def cross_element_escalation(
    element_severities: Dict[str, Severity],
    overlap_pairs: List[Tuple[str, str]],
    min_trigger: Severity = "moderate",
    bump_steps: int = 1,
) -> Dict[str, Severity]:
    updated = dict(element_severities)
    for a, b in overlap_pairs:
        if a not in updated or b not in updated:
            continue
        sa, sb = updated[a], updated[b]
        if severity_ge(sa, min_trigger) and severity_ge(sb, min_trigger):
            if SEVERITY_INDEX[sa] < SEVERITY_INDEX[sb]:
                updated[a] = bump_severity(sa, bump_steps)
            elif SEVERITY_INDEX[sb] < SEVERITY_INDEX[sa]:
                updated[b] = bump_severity(sb, bump_steps)
    return updated


# ----------------------------------------------------------------------
# Automatic inference framework
# ----------------------------------------------------------------------

def automatic_inference_framework(sections: List[SectionMetrics]) -> Dict[str, Any]:
    per_section: List[Dict[str, Severity]] = []

    for m in sections:
        sev_map: Dict[str, Severity] = {}

        sev_map["stream"] = infer_stream_severity(m)
        sev_map["burst"] = infer_burst_severity(m)

        bpm_shift = infer_bpm_shift_severity(m)
        if bpm_shift != "slight":
            sev_map["bpm_shift"] = bpm_shift

        low_bpm_hd = infer_low_bpm_high_density_severity(m)
        if low_bpm_hd:
            sev_map["low_bpm_high_density"] = low_bpm_hd

        hold_int = infer_hold_interference_severity(m)
        if hold_int:
            sev_map["hold_interference"] = hold_int

        tf = infer_trace_flick_severity(m)
        if tf:
            sev_map["trace_flick"] = tf

        read = infer_readability_severity(m)
        if read:
            sev_map["readability"] = read

        temp = infer_temporal_disruption_severity(m)
        if temp:
            sev_map["temporal_disruption"] = temp

        per_section.append(sev_map)

    aggregated: Dict[str, Severity] = {}
    for sev_map in per_section:
        for el, sev in sev_map.items():
            if el not in aggregated or SEVERITY_INDEX[sev] > SEVERITY_INDEX[aggregated[el]]:
                aggregated[el] = sev

    return {
        "per_section": per_section,
        "aggregated": aggregated,
        "notes": (
            "Aggregation uses max severity across sections; "
            "apply cross_element_escalation if overlap data is available."
        ),
    }


# ----------------------------------------------------------------------
# Portable metadata export
# ----------------------------------------------------------------------

def export_rules_to_json() -> Dict[str, Any]:
    return {
        "severity_order": SEVERITY_ORDER,
        "global_severity_semantics": GLOBAL_SEVERITY_SEMANTICS,
        "score_to_severity": [
            {"range": [lo, hi], "severity": sev}
            for (lo, hi), sev in SCORE_TO_SEVERITY
        ],
        "thresholds_by_category": {
            "flow": FLOW_THRESHOLDS,
            "burst": BURST_THRESHOLDS,
            "bpm_shift": BPM_SHIFT_THRESHOLDS,
            "low_bpm_high_density": LOW_BPM_HIGH_DENSITY_THRESHOLDS,
            "hold_interference": HOLD_INTERFERENCE_THRESHOLDS,
            "readability": READABILITY_THRESHOLDS,
            "duration": DURATION_THRESHOLDS,
        },
        "cross_element_escalation_rule": {
            "description": (
                "If two elements overlap and both are >= moderate, "
                "bump the lower one by +1 (cap at demanding)."
            ),
            "min_trigger": "moderate",
            "bump_steps": 1,
        },
    }


def save_rules_json(path: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(export_rules_to_json(), f, ensure_ascii=False, indent=2)


__all__ = [
    "Severity",
    "SEVERITY_ORDER",
    "GLOBAL_SEVERITY_SEMANTICS",
    "map_score_to_severity",
    "infer_stream_severity",
    "infer_burst_severity",
    "infer_bpm_shift_severity",
    "infer_low_bpm_high_density_severity",
    "infer_hold_interference_severity",
    "infer_trace_flick_severity",
    "infer_readability_severity",
    "infer_temporal_disruption_severity",
    "cross_element_escalation",
    "automatic_inference_framework",
    "export_rules_to_json",
    "save_rules_json",
    "SectionMetrics",
]
