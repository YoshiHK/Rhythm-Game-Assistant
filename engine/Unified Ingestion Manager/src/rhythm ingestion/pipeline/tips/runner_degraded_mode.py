from __future__ import annotations
"""runner_degraded_mode.py

Runner-layer helper for degraded-mode propagation and policy.

This module is PURE:
- No file I/O
- No dependencies on Phase 1/2 logic
- Operates only on in-memory canonical_payload dicts

Conventions (written by wiring layers such as severity_engine):
- canonical_payload['diagnostics']['severity_engine']['degraded_mode'|'degraded_reasons']
- canonical_payload['diagnostics']['track_b'|'track_c'|'track_d']['degraded_mode'|'degraded_reasons']

Important semantic fix (latest):
- "Promising tips" gating SHOULD depend on Track C/D capability only.
  Track A (calibration) and Track B (selection) quality may be degraded without
  necessarily forcing Track C/D to be gated.
"""

from typing import Any, Dict, List, Optional, Tuple


def _as_dict(x: Any) -> Optional[Dict[str, Any]]:
    return x if isinstance(x, dict) else None


def _get_block(diag: Dict[str, Any], key: str) -> Optional[Dict[str, Any]]:
    b = _as_dict(diag.get(key))
    return b


def get_degraded_mode_for_track(
    canonical_payload: Dict[str, Any],
    track: str,
    *,
    fallback_to_severity_engine: bool = True,
) -> Tuple[bool, List[str]]:
    """Return (degraded_mode, degraded_reasons) for a given track.

    track accepted values (case-insensitive):
    - Track A: 'track_a', 'severity_engine', 'severity'
    - Track B: 'track_b', 'selector'
    - Track C: 'track_c', 'guidance'
    - Track D: 'track_d', 'narrative'

    If the track-specific block is missing, optionally fall back to severity_engine.
    """

    diag = _as_dict(canonical_payload.get('diagnostics')) or {}
    t = (track or '').strip().lower()

    # Track A / severity engine
    if t in ('track_a', 'a', 'severity', 'severity_engine', 'tracka'):
        block = _get_block(diag, 'severity_engine') or {}
        mode = bool(block.get('degraded_mode'))
        reasons = block.get('degraded_reasons')
        return mode, list(reasons) if isinstance(reasons, list) else []

    # Track B
    if t in ('track_b', 'b', 'selector', 'selection'):
        block = _get_block(diag, 'track_b')
        if block is not None:
            return bool(block.get('degraded_mode')), list(block.get('degraded_reasons') or [])
        if fallback_to_severity_engine:
            return get_degraded_mode_for_track(canonical_payload, 'severity_engine', fallback_to_severity_engine=False)
        return False, []

    # Track C
    if t in ('track_c', 'c', 'guidance', 'guidance_engine'):
        block = _get_block(diag, 'track_c')
        if block is not None:
            return bool(block.get('degraded_mode')), list(block.get('degraded_reasons') or [])
        if fallback_to_severity_engine:
            return get_degraded_mode_for_track(canonical_payload, 'severity_engine', fallback_to_severity_engine=False)
        return False, []

    # Track D
    if t in ('track_d', 'd', 'narrative', 'narrative_module'):
        block = _get_block(diag, 'track_d')
        if block is not None:
            return bool(block.get('degraded_mode')), list(block.get('degraded_reasons') or [])
        if fallback_to_severity_engine:
            return get_degraded_mode_for_track(canonical_payload, 'severity_engine', fallback_to_severity_engine=False)
        return False, []

    # Unknown track label
    if fallback_to_severity_engine:
        return get_degraded_mode_for_track(canonical_payload, 'severity_engine', fallback_to_severity_engine=False)
    return False, []


def is_degraded(
    canonical_payload: Dict[str, Any],
    track: str,
    *,
    fallback_to_severity_engine: bool = True,
) -> bool:
    mode, _ = get_degraded_mode_for_track(
        canonical_payload,
        track,
        fallback_to_severity_engine=fallback_to_severity_engine,
    )
    return bool(mode)


def attach_runner_degraded_snapshot(
    canonical_payload: Dict[str, Any],
    *,
    tracks: Optional[List[str]] = None,
    output_key: str = 'runner_degraded',
) -> Dict[str, Any]:
    """Attach a compact degraded-mode snapshot for runners/observability.

    Adds:
      canonical_payload['diagnostics'][output_key] = {
        'track_a': {'degraded_mode': bool, 'degraded_reasons': [...]},
        'track_b': {...},
        'track_c': {...},
        'track_d': {...},
      }

    Additive and safe.
    """

    tracks = tracks or ['track_a', 'track_b', 'track_c', 'track_d']
    diag = canonical_payload.setdefault('diagnostics', {})
    if not isinstance(diag, dict):
        return canonical_payload

    snap: Dict[str, Any] = {}
    for t in tracks:
        mode, reasons = get_degraded_mode_for_track(canonical_payload, t)
        snap[str(t)] = {
            'degraded_mode': bool(mode),
            'degraded_reasons': list(reasons),
        }

    diag[output_key] = snap
    return canonical_payload


def should_use_promising_tips(
    canonical_payload: Dict[str, Any],
    *,
    prefer_track_specific: bool = True,
) -> bool:
    """Policy helper: whether the runner should treat output as "promising tips".

    Latest fix:
    - ONLY Track C and Track D degradation should gate "promising tips".
    - Track A (calibration) and Track B (selection) may be degraded while
      still allowing C/D to run (with more conservative phrasing handled elsewhere).

    Behavior:
    - If prefer_track_specific=True:
        return False if track_c degraded OR track_d degraded
        else True
    - Else (conservative fallback): gate on severity_engine degraded flag only.

    This function is PURE and never raises.
    """

    if prefer_track_specific:
        c_mode, _ = get_degraded_mode_for_track(canonical_payload, 'track_c')
        if c_mode:
            return False
        d_mode, _ = get_degraded_mode_for_track(canonical_payload, 'track_d')
        if d_mode:
            return False
        return True

    a_mode, _ = get_degraded_mode_for_track(canonical_payload, 'track_a')
    return not bool(a_mode)


__all__ = [
    'get_degraded_mode_for_track',
    'is_degraded',
    'attach_runner_degraded_snapshot',
    'should_use_promising_tips',
]
