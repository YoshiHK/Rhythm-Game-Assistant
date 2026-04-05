"""
rhythm_ingestion.pipeline.section_metrics

Section-level metric definitions and aggregation helpers.

This module defines the *semantic contract* for SectionMetrics produced
during Phase 2 (visual detection and analysis), and provides utilities
to aggregate per-section metrics into chart-level feature representations.

This package is responsible for:
- defining the canonical SectionMetrics shape
- aggregating section metrics across a chart
- exposing stable feature vectors for downstream analysis
  (batch summaries, difficulty profiling, recommendation engine)

This package MUST NOT:
- perform pattern tagging
- generate tips or narrative
- depend on ingestion orchestration
- perform file I/O
"""

from __future__ import annotations

from typing import Dict, Any, List


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
# Aggregation helpers
# ---------------------------------------------------------------------

def aggregate_sections(sections: List[SectionMetrics]) -> Dict[str, Any]:
    """
    Aggregate a list of SectionMetrics into chart-level statistics.

    This function performs *lightweight, deterministic aggregation* only.
    It does NOT apply game-specific logic or normalization.

    Returns a dict of aggregated values suitable for or
    as input to feature extraction.
    """
    if not sections:
        return {}

    def _avg(key: str) -> float:
        vals = [s.get(key) for s in sections if isinstance(s.get(key), (int, float))]
        return sum(vals) / len(vals) if vals else 0.0

    def _max(key: str) -> float:
        vals = [s.get(key) for s in sections if isinstance(s.get(key), (int, float))]
        return max(vals) if vals else 0.0

    return {
        "sections_count": len(sections),
        "avg_nps": _avg("nps"),
        "avg_npb": _avg("npb"),
        "peak_nps": _max("peak_nps_chart"),
        "peak_npb": _max("peak_npb_chart"),
        "avg_hold_coverage": _avg("hold_coverage"),
        "avg_lane_cross_rate": _avg("lane_cross_rate"),
        "avg_spacing_variance": _avg("spacing_variance"),
        "bpm_shift_count": sum(
            s.get("bpm_shift_count", 0) for s in sections if isinstance(s.get("bpm_shift_count"), int)
        ),
        "chart_stop_count": sum(
            s.get("chart_stop_count", 0) for s in sections if isinstance(s.get("chart_stop_count"), int)
        ),
    }


# ---------------------------------------------------------------------
# Feature vector extraction
# ---------------------------------------------------------------------

def build_section_feature_vector(
    sections: List[SectionMetrics],
) -> Dict[str, float]:
    """
    Convert SectionMetrics into a normalized chart-level feature vector.

    This function defines the *semantic bridge* between raw metrics
    and higher-level reasoning (difficulty profiling, recommendations).

    No thresholds or interpretation logic are applied here.
    """
    agg = aggregate_sections(sections)

    if not agg:
        return {}

    return {
        # Density & speed
        "avg_nps": float(agg.get("avg_nps", 0.0)),
        "peak_nps": float(agg.get("peak_nps", 0.0)),

        # Rhythm stability
        "avg_npb": float(agg.get("avg_npb", 0.0)),
        "peak_npb": float(agg.get("peak_npb", 0.0)),

        # Technique load
        "hold_ratio": float(agg.get("avg_hold_coverage", 0.0)),
        "lane_cross_rate": float(agg.get("avg_lane_cross_rate", 0.0)),
        "spacing_variance": float(agg.get("avg_spacing_variance", 0.0)),

        # Structural volatility
        "bpm_shift_count": float(agg.get("bpm_shift_count", 0)),
        "chart_stop_count": float(agg.get("chart_stop_count", 0)),
    }


__all__ = [
    "SECTION_METRICS_VERSION",
    "SectionMetrics",
    "aggregate_sections",
    "build_section_feature_vector",
]
``
