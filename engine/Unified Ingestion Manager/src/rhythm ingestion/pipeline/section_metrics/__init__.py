from __future__ import annotations

"""
rhythm_ingestion.pipeline.section_metrics

Section-level metric definitions and aggregation helpers.

This module defines the semantic contract for SectionMetrics produced
during Phase 2 (visual detection and analysis), and provides utilities
to aggregate per-section metrics into chart-level feature representations.

Responsibilities:
- define the canonical SectionMetrics shape
- aggregate section metrics across a chart
- expose stable feature vectors for downstream analysis
  (batch summaries, difficulty profiling, recommendation engine)

This module MUST NOT:
- perform pattern tagging
- generate tips or narrative
- depend on ingestion orchestration
- perform file I/O
"""

from typing import Any, Dict, List

# ---------------------------------------------------------------------
# Versioning
# ---------------------------------------------------------------------

SECTION_METRICS_VERSION = "section_metrics_v1"

# ---------------------------------------------------------------------
# Canonical SectionMetrics contract
# ---------------------------------------------------------------------

SectionMetrics = Dict[str, Any]
"""
Canonical SectionMetrics dictionary.

Expected keys (produced by Phase 2 detectors, not enforced here):
- duration_sec
- bpm
- npb
- nps
- avg_npb_chart
- avg_nps_chart
- peak_npb_chart
- peak_nps_chart
- rest_ratio
- hold_coverage
- notes_during_hold_ratio
- slide_cross_lane_rate
- trace_flick_count
- flick_density
- overlap_ratio
- lane_cross_rate
- spacing_variance
- bpm_delta_ratio
- bpm_shift_count
- chart_stop_count
- fake_end_flag
"""

# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------

_NUMERIC_KEYS = [
    "duration_sec",
    "bpm",
    "npb",
    "nps",
    "avg_npb_chart",
    "avg_nps_chart",
    "peak_npb_chart",
    "peak_nps_chart",
    "rest_ratio",
    "hold_coverage",
    "notes_during_hold_ratio",
    "slide_cross_lane_rate",
    "trace_flick_count",
    "flick_density",
    "overlap_ratio",
    "lane_cross_rate",
    "spacing_variance",
    "bpm_delta_ratio",
    "bpm_shift_count",
    "chart_stop_count",
]

_BOOL_KEYS = [
    "fake_end_flag",
]


def _safe_float(x: Any, default: float = 0.0) -> float:
    try:
        if x is None:
            return default
        return float(x)
    except Exception:
        return default


def _safe_bool(x: Any) -> bool:
    if isinstance(x, bool):
        return x
    if isinstance(x, (int, float)):
        return bool(x)
    if isinstance(x, str):
        s = x.strip().lower()
        return s in {"1", "true", "yes", "y", "on"}
    return False


# ---------------------------------------------------------------------
# Aggregation helpers
# ---------------------------------------------------------------------

def aggregate_sections(sections: List[SectionMetrics]) -> Dict[str, Any]:
    """
    Aggregate a list of SectionMetrics into chart-level statistics.

    Behavior:
    - numeric keys are averaged across sections
    - boolean keys are OR-reduced
    - section_count is always included
    """
    if not sections:
        out: Dict[str, Any] = {"section_count": 0}
        for k in _NUMERIC_KEYS:
            out[k] = 0.0
        for k in _BOOL_KEYS:
            out[k] = False
        return out

    out: Dict[str, Any] = {"section_count": len(sections)}

    for key in _NUMERIC_KEYS:
        values = [_safe_float(s.get(key, 0.0)) for s in sections]
        out[key] = sum(values) / len(values) if values else 0.0

    for key in _BOOL_KEYS:
        out[key] = any(_safe_bool(s.get(key, False)) for s in sections)

    return out


# ---------------------------------------------------------------------
# Feature vector extraction
# ---------------------------------------------------------------------

def build_section_feature_vector(
    sections: List[SectionMetrics],
) -> Dict[str, float]:
    """
    Convert SectionMetrics into a normalized chart-level feature vector.

    Current contract:
    - returns averaged numeric aggregation fields as float values
    - encodes boolean flags as 0.0 / 1.0
    - includes section_count as float
    """
    agg = aggregate_sections(sections)

    feature_vector: Dict[str, float] = {
        "section_count": float(agg.get("section_count", 0)),
    }

    for key in _NUMERIC_KEYS:
        feature_vector[key] = _safe_float(agg.get(key, 0.0))

    for key in _BOOL_KEYS:
        feature_vector[key] = 1.0 if _safe_bool(agg.get(key, False)) else 0.0

    return feature_vector


__all__ = [
    "SECTION_METRICS_VERSION",
    "SectionMetrics",
    "aggregate_sections",
    "build_section_feature_vector",
]