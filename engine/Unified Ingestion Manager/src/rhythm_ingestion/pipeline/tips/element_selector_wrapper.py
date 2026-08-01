from __future__ import annotations
"""element_selector_wrapper.py

Phase 3 wiring wrapper for Track B element selection.

This is a governance wrapper around Completed Phase selector_v2.select_elements_v2.

Latest fix includes:
1) Selection diagnostics semantics
   - schema_missing
   - selector_failure (exception)
   - selector_empty_output
   - fallback_sort_used
   - empty_input

2) Tone hints (wiring-only, non-breaking)
   - Defines a small Tone enum (Literal)
   - Derives a tone_hint when Track B is degraded
   - Attaches tone_hint to:
       a) canonical_payload['diagnostics']['tone_hint'] (non-overwriting, strongest wins)
       b) canonical_payload['diagnostics']['track_b']['tone_hint']
       c) each selected element dict (field: 'tone_hint')

Important semantic note
- Track B degraded does NOT automatically gate Track C/D. Promising tips gating
  is driven ONLY by Track C/D degraded flags (see runner_degraded_mode.py).

"""

from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple, Literal


# ----------------------------
# Public tone enum
# ----------------------------

Tone = Literal['normal', 'neutral', 'minimal']


DEFAULT_SCHEMA_PATH = 'proseka_internal_analysis_schema_v1.4.0.json'
DEFAULT_CALIBRATION_CONFIG_PATH = 'score_calibration_config_v0.2.1.json'


def _safe_float(x: Any, default: float = 0.0) -> float:
    try:
        if x is None:
            return default
        return float(x)
    except Exception:
        return default


def _severity_rank(sev: Any) -> int:
    order = ['slight', 'light', 'mild', 'moderate', 'dense', 'complex', 'demanding']
    idx = {s: i for i, s in enumerate(order)}
    try:
        return idx.get(str(sev), 0)
    except Exception:
        return 0


def _target_count_for_difficulty(difficulty: str) -> int:
    d = (difficulty or '').strip().lower()
    if d == 'append':
        return 4
    return 3


def _tone_strength(t: Tone) -> int:
    # Higher means stronger / more conservative.
    return {'normal': 0, 'neutral': 1, 'minimal': 2}.get(t, 0)


def _derive_tone_hint(track_b_reasons: Sequence[str]) -> Tone:
    """Derive a tone hint from Track B degraded reasons."""
    rs = set([str(r) for r in (track_b_reasons or [])])
    if 'empty_input' in rs:
        return 'minimal'
    if rs:
        return 'neutral'
    return 'normal'


def _attach_tone_hint(canonical_payload: Dict[str, Any], tone: Tone) -> None:
    """Attach tone hint additively; strongest wins; never throws."""
    diag = canonical_payload.setdefault('diagnostics', {})
    if not isinstance(diag, dict):
        return

    current = diag.get('tone_hint')
    cur_tone: Tone = 'normal'
    if isinstance(current, str) and current in ('normal', 'neutral', 'minimal'):
        cur_tone = current  # type: ignore

    if _tone_strength(tone) > _tone_strength(cur_tone):
        diag['tone_hint'] = tone


def _calibrate_elements_if_possible(
    *,
    game_id: str,
    elements_skeleton: List[Dict[str, Any]],
    sections: Optional[List[Any]],
    calibration_config_path: str,
    preserve_severity: bool = True,
) -> Tuple[List[Dict[str, Any]], bool, Optional[str]]:
    """Best-effort score calibration.

    Returns (elements_out, used_calibration, note).
    """

    gid = (game_id or '').strip().lower()
    if gid and gid != 'proseka':
        return elements_skeleton, False, None

    if not isinstance(sections, list) or not sections:
        return elements_skeleton, False, 'no_sections'

    try:
        from . import proseka_score_calibration as _cal  # type: ignore
    except Exception:
        try:
            import proseka_score_calibration as _cal  # type: ignore
        except Exception:
            return elements_skeleton, False, 'calibrator_missing'

    try:
        cfg = _cal.load_calibration_config(calibration_config_path)  # type: ignore
    except Exception:
        return elements_skeleton, False, 'config_unreadable'

    try:
        if hasattr(_cal, 'calibrate_elements_skeleton'):
            out = _cal.calibrate_elements_skeleton(
                elements_skeleton,
                list(sections),
                cfg,
                preserve_severity=preserve_severity,
            )  # type: ignore
            return (out if isinstance(out, list) else elements_skeleton), True, None
    except Exception:
        return elements_skeleton, False, 'calibration_failed'

    return elements_skeleton, False, 'calibration_unavailable'


def select_elements_phase3(
    *,
    game_id: str,
    canonical_payload: Dict[str, Any],
    difficulty: str,
    schema_path: str = DEFAULT_SCHEMA_PATH,
    enable_calibration_if_possible: bool = True,
    calibration_config_path: str = DEFAULT_CALIBRATION_CONFIG_PATH,
    preserve_severity: bool = True,
    attach_to_payload: bool = True,
    output_key: str = 'selected_elements',
) -> List[Dict[str, Any]]:
    """Phase 3 Track B wrapper.

    - If elements_skeleton is empty: return [] and record empty_input.
    - Optionally calibrate scores (best-effort).
    - Attempt selector_v2.select_elements_v2.
    - If schema missing, selector raises, or selector returns empty: use fallback_sort.

    Writes diagnostics under canonical_payload['diagnostics']['track_b'].
    Also attaches tone hints when degraded.
    """

    diag_root = canonical_payload.setdefault('diagnostics', {})
    if not isinstance(diag_root, dict):
        diag_root = {}
        canonical_payload['diagnostics'] = diag_root

    track_b_diag = diag_root.setdefault('track_b', {})
    if not isinstance(track_b_diag, dict):
        track_b_diag = {}
        diag_root['track_b'] = track_b_diag

    elements = canonical_payload.get('elements_skeleton')
    elements_skeleton: List[Dict[str, Any]] = elements if isinstance(elements, list) else []
    sections = canonical_payload.get('sections')

    reasons: List[str] = []
    used_cal = False
    cal_note: Optional[str] = None

    if not elements_skeleton:
        reasons = ['empty_input']
        tone = _derive_tone_hint(reasons)
        _attach_tone_hint(canonical_payload, tone)
        track_b_diag.update({
            'degraded_mode': True,
            'degraded_reasons': reasons,
            'tone_hint': tone,
            'selector': 'none',
            'input_count': 0,
            'selected_count': 0,
        })
        if attach_to_payload:
            canonical_payload[output_key] = []
        return []

    if enable_calibration_if_possible:
        elements_skeleton, used_cal, cal_note = _calibrate_elements_if_possible(
            game_id=game_id,
            elements_skeleton=elements_skeleton,
            sections=sections if isinstance(sections, list) else None,
            calibration_config_path=calibration_config_path,
            preserve_severity=preserve_severity,
        )

    # Detect schema existence early
    try:
        schema_exists = Path(schema_path).exists()
    except Exception:
        schema_exists = False

    if not schema_exists:
        reasons.append('schema_missing')

    # Import selector_v2
    selector_mod = None
    try:
        from . import selector_v2 as selector_mod  # type: ignore
    except Exception:
        try:
            import selector_v2 as selector_mod  # type: ignore
        except Exception:
            selector_mod = None

    selected: List[Dict[str, Any]] = []
    selector_used = 'selector_v2'
    selector_error: Optional[str] = None

    if selector_mod is not None and hasattr(selector_mod, 'select_elements_v2') and schema_exists:
        try:
            selected = selector_mod.select_elements_v2(
                elements_skeleton,
                difficulty=str(difficulty or ''),
                schema_path=schema_path,
            )  # type: ignore
            if not isinstance(selected, list):
                selected = []
        except Exception as e:
            selector_error = f'{type(e).__name__}: {e}'
            reasons.append('selector_failure')
            selected = []

    # Empty output -> fallback
    if not selected:
        if schema_exists and selector_error is None and selector_mod is not None:
            reasons.append('selector_empty_output')
        selector_used = 'fallback_sort'
        if selector_used == 'fallback_sort' and 'fallback_sort_used' not in reasons:
            reasons.append('fallback_sort_used')
        sortable = [e for e in elements_skeleton if isinstance(e, dict)]
        sortable.sort(key=lambda d: (
            -_safe_float(d.get('score'), 0.0),
            -_severity_rank(d.get('severity')),
            -_safe_float(d.get('section_coverage'), 0.0),
            str(d.get('element_name') or ''),
        ))
        k = _target_count_for_difficulty(str(difficulty or ''))
        selected = sortable[:k]

    degraded_mode = bool(reasons)
    tone = _derive_tone_hint(reasons)

    # Attach tone hint to payload diagnostics (strongest wins)
    if degraded_mode:
        _attach_tone_hint(canonical_payload, tone)

    # Attach tone hint into selected element dicts (non-breaking)
    if tone != 'normal':
        for el in selected:
            if isinstance(el, dict) and 'tone_hint' not in el:
                el['tone_hint'] = tone

    track_b_diag.update({
        'degraded_mode': degraded_mode,
        'degraded_reasons': reasons,
        'tone_hint': tone,
        'selector': selector_used,
        'schema_path': schema_path,
        'schema_exists': bool(schema_exists),
        'input_count': len(elements_skeleton),
        'selected_count': len(selected),
        'used_calibration': bool(used_cal),
    })
    if cal_note:
        track_b_diag['calibration_note'] = cal_note
    if selector_error:
        track_b_diag['selector_error'] = selector_error

    if attach_to_payload:
        canonical_payload[output_key] = selected

    return selected


__all__ = ['Tone', 'select_elements_phase3']
