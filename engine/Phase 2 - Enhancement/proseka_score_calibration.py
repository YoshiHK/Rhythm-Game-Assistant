"""proseka_score_calibration.py

Phase 2 Track A: scoring + severity calibration utilities.

This module is designed to be non-breaking:
- It does NOT change any schemas.
- It can be used as a wrapper around (5.1) severity_detector.infer_severities_for_chart.

Key idea
- Phase 1 uses severity bin midpoints as score.
- Phase 2 optionally calibrates score with a feature model.

Inputs expected
- sections: list[SectionMetrics] produced upstream (e.g. chart_visual_detector_merged).
- per-element skeleton output from severity_detector.

Outputs
- identical to severity_detector, but with calibrated scores (and optionally calibrated severities).

"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple
import json
import math

# Import types and base inference
from severity_detector import infer_severities_for_chart

# Import severity utilities
from proseka_severity_rules import (
    Severity,
    SEVERITY_ORDER,
    SEVERITY_INDEX,
    SCORE_TO_SEVERITY,
    map_score_to_severity,
)


def _clamp01(x: float) -> float:
    if x < 0.0:
        return 0.0
    if x > 1.0:
        return 1.0
    return x


def _sigmoid(x: float) -> float:
    # numerically stable sigmoid
    if x >= 0:
        z = math.exp(-x)
        return 1.0 / (1.0 + z)
    else:
        z = math.exp(x)
        return z / (1.0 + z)


def load_calibration_config(path: str) -> Dict[str, Any]:
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def severity_midpoint(sev: Severity, cfg: Optional[Dict[str, Any]] = None) -> float:
    """Return a representative score for a severity.

    Default: bin midpoint from SCORE_TO_SEVERITY.
    Optional override via cfg['severity_midpoints_override'].
    """
    if cfg and cfg.get('severity_midpoints_override', {}).get('enabled'):
        mp = cfg['severity_midpoints_override'].get('midpoints', {})
        if sev in mp:
            return float(mp[sev])

    for (lo, hi), s in SCORE_TO_SEVERITY:
        if s == sev:
            return (lo + hi) / 2.0

    # fallback: normalized rank
    idx = SEVERITY_INDEX.get(sev, 0)
    return idx / max(SEVERITY_INDEX.values() or [1])


def sections_to_features(sections: List[Any]) -> Dict[str, float]:
    """Compute a compact feature set from SectionMetrics list.

    This is intentionally simple and only uses fields that exist in SectionMetrics
    produced by chart_visual_detector_merged.
    """
    if not sections:
        return {
            'peak_density_mult': 1.0,
            'avg_density_mult': 1.0,
            'density_variance': 0.0,
            'rest_ratio_inverse': 0.0,
            'hold_interference_proxy': 0.0,
            'readability_proxy': 0.0,
            'temporal_disruption_proxy': 0.0,
            'bpm_shift_proxy': 0.0,
        }

    # density multipliers
    mults = []
    rests = []
    holds = []
    overlaps = []
    stops = []
    bpm_deltas = []
    notes_during_hold = []

    for m in sections:
        avg_npb = getattr(m, 'avg_npb_chart', 0.0) or 0.0
        npb = getattr(m, 'npb', 0.0) or 0.0
        if avg_npb > 0:
            mults.append(npb / avg_npb)
        rests.append(getattr(m, 'rest_ratio', 0.0) or 0.0)
        holds.append(getattr(m, 'hold_coverage', 0.0) or 0.0)
        overlaps.append(getattr(m, 'overlap_ratio', 0.0) or 0.0)
        stops.append(getattr(m, 'chart_stop_count', 0) or 0)
        bpm_deltas.append(getattr(m, 'bpm_delta_ratio', 0.0) or 0.0)
        notes_during_hold.append(getattr(m, 'notes_during_hold_ratio', 0.0) or 0.0)

    if not mults:
        mults = [1.0]

    peak_mult = max(mults)
    avg_mult = sum(mults) / len(mults)
    var = sum((x - avg_mult) ** 2 for x in mults) / len(mults)

    rest_inv = 1.0 - (sum(rests) / len(rests))
    hold_proxy = sum(notes_during_hold) / len(notes_during_hold)
    read_proxy = sum(overlaps) / len(overlaps)
    temp_proxy = 1.0 if any(s > 0 for s in stops) else 0.0
    bpm_proxy = min(1.0, sum(1 for d in bpm_deltas if abs(d) >= 0.15) / max(1, len(bpm_deltas)))

    return {
        'peak_density_mult': float(peak_mult),
        'avg_density_mult': float(avg_mult),
        'density_variance': float(var),
        'rest_ratio_inverse': float(rest_inv),
        'hold_interference_proxy': float(hold_proxy),
        'readability_proxy': float(read_proxy),
        'temporal_disruption_proxy': float(temp_proxy),
        'bpm_shift_proxy': float(bpm_proxy),
    }


def calibrated_chart_score(features: Dict[str, float], cfg: Dict[str, Any]) -> float:
    """Compute a calibrated score for the chart (0..1).

    Enabled when cfg['feature_model']['enabled'] is True.
    """
    fm = cfg.get('feature_model', {})
    if not fm.get('enabled'):
        return 0.0

    weights = fm.get('weights', {})
    bias = float(fm.get('bias', 0.0))

    z = bias
    for k, w in weights.items():
        z += float(w) * float(features.get(k, 0.0))

    squash = fm.get('squash', 'sigmoid')
    if squash == 'sigmoid':
        s = _sigmoid(z)
    else:
        # linear fallback
        s = z

    post = fm.get('post_scale', {})
    lo = float(post.get('min', 0.0))
    hi = float(post.get('max', 1.0))

    return _clamp01(lo + (hi - lo) * s)


def calibrate_elements_skeleton(
    elements_skeleton: List[Dict[str, Any]],
    sections: List[Any],
    cfg: Dict[str, Any],
    *,
    preserve_severity: bool = True
) -> List[Dict[str, Any]]:
    """Apply calibration to element scores (and optionally severities).

    Default behavior:
    - If feature_model is disabled: use severity_midpoint (with optional overrides).
    - If feature_model is enabled: blend midpoint with calibrated chart score.

    Blending keeps relative element ordering but shifts global score calibration.
    """
    feats = sections_to_features(sections)
    chart_s = calibrated_chart_score(feats, cfg) if cfg.get('feature_model', {}).get('enabled') else None

    # Blend factor: how much of chart-level calibration to apply
    blend = float(cfg.get('feature_model', {}).get('blend', 0.35))

    out = []
    for el in elements_skeleton:
        sev = el.get('severity')
        if sev is None:
            out.append(el)
            continue

        # Base score from severity midpoint
        base = severity_midpoint(sev, cfg)

        if chart_s is not None:
            score = _clamp01((1.0 - blend) * base + blend * chart_s)
        else:
            score = _clamp01(base)

        el2 = dict(el)
        el2['score'] = score

        if not preserve_severity:
            el2['severity'] = map_score_to_severity(score)

        out.append(el2)

    return out


def infer_severities_for_chart_calibrated(
    sections: List[Any],
    *,
    calibration_config_path: str,
    preserve_severity: bool = True,
    coverage_threshold: Optional[str] = None,
) -> Dict[str, Any]:
    """Drop-in replacement for severity_detector.infer_severities_for_chart.

    - Runs base inference
    - Optionally re-scores elements via calibration config

    This does NOT change section_coverage unless you set coverage_threshold.
    """
    cfg = load_calibration_config(calibration_config_path)

    # Base inference
    base = infer_severities_for_chart(
        sections,
        coverage_threshold=coverage_threshold or cfg.get('coverage', {}).get('threshold', 'moderate')
    )

    elements = base.get('elements_skeleton', []) or []
    base['elements_skeleton'] = calibrate_elements_skeleton(
        elements,
        sections,
        cfg,
        preserve_severity=preserve_severity,
    )

    return base


__all__ = [
    'load_calibration_config',
    'severity_midpoint',
    'sections_to_features',
    'infer_severities_for_chart_calibrated',
]
