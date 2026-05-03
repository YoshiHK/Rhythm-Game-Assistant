#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""validator_ongeki.py

UMI Phase 3 validator for ONGEKI.

Scope (Phase 3 only):
- Structural validation of canonical rows emitted by adapter_ongeki.py
- No gameplay semantics, no tips, no Phase 4/5 logic
- Conservative: prefer warnings over hard failures when data is partial

Schema-driven thresholds (policy knobs) are read from:
  ongeki.json -> gating.phase4.timing_surface.requirements

All warnings emitted by this validator include:
- schema_key: primary controlling schema node
- schema_keys: list of controlling schema nodes (multiple control points)
- schema_key_labels: human-readable labels for schema_keys (UNTRUNCATED)
- schema_key_notes: full notes (untruncated) for schema_keys

Labels prefer schema notes; if absent, a fallback human-readable description is generated
from the schema key path.

This is wiring/validation only; it does not modify completed phases.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
import math
from pathlib import Path

try:
    from .base_validator_v2 import BaseValidatorV2, ValidationResult  # type: ignore
except Exception:  # pragma: no cover
    BaseValidatorV2 = object  # type: ignore
    ValidationResult = Dict[str, Any]  # type: ignore

try:
    from .common_validator_utils import build_validation_ok, build_validation_fail, safe_int  # type: ignore
except Exception:  # pragma: no cover
    def build_validation_ok(game_id: str, warnings: Optional[List[Dict[str, Any]]] = None, diagnostics: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        return {"ok": True, "game_id": game_id, "errors": [], "warnings": warnings or [], "diagnostics": diagnostics or {}}

    def build_validation_fail(game_id: str, errors: List[Dict[str, Any]], warnings: Optional[List[Dict[str, Any]]] = None, diagnostics: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        return {"ok": False, "game_id": game_id, "errors": errors, "warnings": warnings or [], "diagnostics": diagnostics or {}}

    def safe_int(x: Any, default: Optional[int] = None) -> Optional[int]:
        try:
            return int(x)
        except Exception:
            return default


# ----------------------------
# Schema context (requirements + labels + full notes)
# ----------------------------

_SCHEMA_CACHE: Dict[str, Tuple[Dict[str, Any], Dict[str, str], Dict[str, str], str]] = {}


def _fallback_label_from_schema_key(k: str) -> str:
    """Generate a human-readable label from a schema key path.

    This is used only when schema notes are not available for a key.

    Examples:
      gating.phase4.timing_surface -> Phase 4 timing surface gate
      gating.phase4.timing_surface.requirements.tick_grid_warning_cap ->
        Phase 4 timing surface requirement: tick grid warning cap
    """
    if not isinstance(k, str) or not k:
        return str(k)

    parts = k.split('.')

    # Common known prefix
    if len(parts) >= 2 and parts[0] == 'gating' and parts[1] == 'phase4':
        phase = 'Phase 4'
        # Determine component
        if 'timing_surface' in parts:
            if 'requirements' in parts:
                tail = parts[parts.index('requirements') + 1:]
                tail_txt = ' '.join(t.replace('_', ' ') for t in tail).strip()
                return f"{phase} timing surface requirement: {tail_txt}" if tail_txt else f"{phase} timing surface requirement"
            return f"{phase} timing surface gate"
        # fallback other gates
        tail_txt = ' '.join(t.replace('_', ' ') for t in parts[2:]).strip()
        return f"{phase} gate: {tail_txt}" if tail_txt else f"{phase} gate"

    # Generic fallback: last segment
    return parts[-1].replace('_', ' ')


def _load_schema_context() -> Tuple[Dict[str, Any], Dict[str, str], Dict[str, str], str]:
    """Load schema requirements and derive labels + full notes.

    UNTRUNCATED labels:
    - If a note exists, labels[schema_key] == note (full text)
    - Otherwise labels[schema_key] == fallback label derived from schema_key

    Notes sources:
    - gating.phase4.timing_surface.notes
    - gating.phase4.timing_surface.requirements.<k>_notes
    """

    cache_key = 'ongeki_schema_context'
    if cache_key in _SCHEMA_CACHE:
        return _SCHEMA_CACHE[cache_key]

    default_req: Dict[str, Any] = {
        "tick_ge_resolution_ratio_threshold": 0.05,
        "tick_grid_warning_cap": 50,
        "time_beats_monotonic_epsilon": 1e-9,
    }

    here = Path(__file__).resolve().parent
    candidates = [
        here / 'ongeki.json',
        here / 'analysis_schema.ongeki.v1.json',
        here / 'schemas' / 'ongeki.json',
        here / 'schemas' / 'analysis_schema.ongeki.v1.json',
        here / 'analysis_schemas' / 'ongeki.json',
        here / 'analysis_schemas' / 'analysis_schema.ongeki.v1.json',
        here.parent / 'schemas' / 'ongeki.json',
        here.parent / 'schemas' / 'analysis_schema.ongeki.v1.json',
    ]

    import json

    labels: Dict[str, str] = {"gating.phase4.timing_surface": "Phase 4 timing surface gate"}
    notes: Dict[str, str] = {}

    for p in candidates:
        try:
            if not p.exists():
                continue
            raw = json.loads(p.read_text(encoding='utf-8'))
            timing_surface = (((raw.get('gating') or {}).get('phase4') or {}).get('timing_surface') or {})
            req = timing_surface.get('requirements')
            if not isinstance(req, dict):
                continue

            merged = dict(default_req)
            merged.update(req)

            base_key = 'gating.phase4.timing_surface'
            base_note = timing_surface.get('notes')
            if isinstance(base_note, str) and base_note.strip():
                notes[base_key] = base_note
                labels[base_key] = base_note
            else:
                labels[base_key] = _fallback_label_from_schema_key(base_key)

            for k in req.keys():
                if not isinstance(k, str) or k.endswith('_notes'):
                    continue
                schema_key = f"gating.phase4.timing_surface.requirements.{k}"
                note_key = f"{k}_notes"
                note_val = req.get(note_key)
                if isinstance(note_val, str) and note_val.strip():
                    notes[schema_key] = note_val
                    labels[schema_key] = note_val
                else:
                    labels[schema_key] = _fallback_label_from_schema_key(schema_key)

            _SCHEMA_CACHE[cache_key] = (merged, labels, notes, str(p))
            return merged, labels, notes, str(p)
        except Exception:
            continue

    # Default fallback
    base_key = 'gating.phase4.timing_surface'
    labels.setdefault(base_key, _fallback_label_from_schema_key(base_key))
    _SCHEMA_CACHE[cache_key] = (default_req, labels, notes, 'default')
    return default_req, labels, notes, 'default'


def _get_float_req(key: str, default: float) -> Tuple[float, str]:
    req, _labels, _notes, src = _load_schema_context()
    v = req.get(key, default)
    try:
        return float(v), src
    except Exception:
        return float(default), src


def _get_int_req(key: str, default: int) -> Tuple[int, str]:
    req, _labels, _notes, src = _load_schema_context()
    v = req.get(key, default)
    try:
        return int(v), src
    except Exception:
        return int(default), src


def _label_for_schema_key(k: str) -> str:
    _req, labels, _notes, _src = _load_schema_context()
    v = labels.get(k)
    if isinstance(v, str) and v.strip():
        return v
    return _fallback_label_from_schema_key(k)


def _note_for_schema_key(k: str) -> str:
    _req, _labels, notes, _src = _load_schema_context()
    return notes.get(k, '')


# ----------------------------
# Warning builder
# ----------------------------

def _w(*, code: str, schema_key: str, schema_keys: Optional[List[str]] = None, message: str, source: str, **extra: Any) -> Dict[str, Any]:
    keys = schema_keys[:] if isinstance(schema_keys, list) else [schema_key]
    if schema_key not in keys:
        keys.insert(0, schema_key)

    seen = set()
    dedup: List[str] = []
    for k in keys:
        if not isinstance(k, str) or k in seen:
            continue
        seen.add(k)
        dedup.append(k)

    labels = {k: _label_for_schema_key(k) for k in dedup}
    full_notes = {k: _note_for_schema_key(k) for k in dedup if _note_for_schema_key(k)}

    out: Dict[str, Any] = {
        'code': code,
        'schema_key': schema_key,
        'schema_keys': dedup,
        'schema_key_labels': labels,
        'schema_key_notes': full_notes,
        'message': message,
        'source': source,
    }
    out.update(extra)
    return out


# ----------------------------
# Helpers
# ----------------------------

def _is_number(x: Any) -> bool:
    return isinstance(x, (int, float)) and x == x


def _extract_resolution_from_sections(sections: Any) -> Optional[int]:
    if not isinstance(sections, list):
        return None
    for sec in sections:
        if isinstance(sec, dict) and sec.get('timing_surface_only') is True:
            rr = safe_int(sec.get('resolution'))
            if isinstance(rr, int) and rr > 0:
                return rr
    return None


def _iter_timing_event_streams(sections: Any) -> Dict[str, List[Dict[str, Any]]]:
    out: Dict[str, List[Dict[str, Any]]] = {'bpm_events': [], 'meter_events': [], 'soflan_events': []}
    if not isinstance(sections, list):
        return out
    for sec in sections:
        if not isinstance(sec, dict):
            continue
        tp = sec.get('timing_positions')
        if not isinstance(tp, dict):
            continue
        for k in out.keys():
            arr = tp.get(k)
            if isinstance(arr, list):
                for ev in arr:
                    if isinstance(ev, dict):
                        out[k].append(ev)
    return out


# ----------------------------
# Checks
# ----------------------------

def _tick_checks(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    warns: List[Dict[str, Any]] = []
    sections = payload.get('sections')
    streams = _iter_timing_event_streams(sections)
    all_events: List[Dict[str, Any]] = []
    for lst in streams.values():
        all_events.extend(lst)

    if not any(ev.get('tick') is not None for ev in all_events):
        return warns

    resolution = _extract_resolution_from_sections(sections)
    base_key = 'gating.phase4.timing_surface'

    if resolution is None:
        warns.append(_w(
            code='O_RESOLUTION_MISSING_FOR_TICK',
            schema_key=base_key,
            schema_keys=[base_key],
            message="Timing events include 'tick' but no positive 'resolution' found in sections; cannot validate tick bounds.",
            source='validator_ongeki.tick_range',
        ))
        return warns

    tick_total = 0
    tick_ge = 0

    for i, ev in enumerate(all_events):
        t = safe_int(ev.get('tick'))
        if t is None:
            continue
        tick_total += 1
        if t < 0:
            warns.append(_w(
                code='O_TICK_OUT_OF_RANGE',
                schema_key=base_key,
                schema_keys=[base_key],
                message=f"Timing event #{i} has tick < 0 (tick={t}).",
                source='validator_ongeki.tick_range',
                resolution=resolution,
            ))
        elif t >= resolution:
            tick_ge += 1
            warns.append(_w(
                code='O_TICK_OUT_OF_RANGE',
                schema_key=base_key,
                schema_keys=[base_key],
                message=f"Timing event #{i} has tick >= resolution (tick={t}, resolution={resolution}).",
                source='validator_ongeki.tick_range',
                resolution=resolution,
            ))

    if tick_total > 0:
        ratio = float(tick_ge) / float(tick_total)
        thr, thr_src = _get_float_req('tick_ge_resolution_ratio_threshold', 0.05)
        thr_key = 'gating.phase4.timing_surface.requirements.tick_ge_resolution_ratio_threshold'
        if ratio >= thr:
            warns.append(_w(
                code='O_TICK_GE_RESOLUTION_RATIO',
                schema_key=thr_key,
                schema_keys=[thr_key, base_key],
                message=(
                    f"High ratio of ticks >= resolution: {tick_ge}/{tick_total} ({ratio:.1%}) with resolution={resolution}. "
                    "This may indicate incorrect resolution inference or malformed measure/tick positions."
                ),
                source='validator_ongeki.tick_range',
                resolution=resolution,
                tick_total=tick_total,
                tick_ge_resolution=tick_ge,
                ratio=ratio,
                threshold=thr,
                threshold_source=thr_src,
            ))

    return warns


def _measure_negative_checks(streams: Dict[str, List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    warns: List[Dict[str, Any]] = []
    base_key = 'gating.phase4.timing_surface'
    for stream, events in streams.items():
        for i, ev in enumerate(events):
            m = safe_int(ev.get('measure'))
            if m is not None and m < 0:
                warns.append(_w(
                    code='O_MEASURE_NEGATIVE',
                    schema_key=base_key,
                    schema_keys=[base_key],
                    message=f"{stream} event #{i} has measure < 0 (measure={m}).",
                    source='validator_ongeki.measure',
                ))
    return warns


def _time_beats_monotonicity_checks(streams: Dict[str, List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    warns: List[Dict[str, Any]] = []
    eps, eps_src = _get_float_req('time_beats_monotonic_epsilon', 1e-9)
    eps_key = 'gating.phase4.timing_surface.requirements.time_beats_monotonic_epsilon'
    base_key = 'gating.phase4.timing_surface'

    for stream, events in streams.items():
        sortable = []
        for idx, ev in enumerate(events):
            m = safe_int(ev.get('measure'))
            t = safe_int(ev.get('tick'))
            tb = ev.get('time_beats')
            if m is None or t is None or not _is_number(tb):
                continue
            sortable.append((m, t, float(tb), idx))
        if len(sortable) < 2:
            continue
        sortable.sort(key=lambda x: (x[0], x[1], x[3]))
        prev_m, prev_t, prev_tb, prev_idx = sortable[0][0], sortable[0][1], sortable[0][2], sortable[0][3]
        for m, t, tb, idx in sortable[1:]:
            if tb + eps < prev_tb:
                warns.append(_w(
                    code='O_TIME_BEATS_NON_MONOTONIC',
                    schema_key=eps_key,
                    schema_keys=[eps_key, base_key],
                    message=(
                        f"{stream} time_beats decreases at event #{idx} (measure={m}, tick={t}, time_beats={tb}) "
                        f"< previous (measure={prev_m}, tick={prev_t}, time_beats={prev_tb})."
                    ),
                    source='validator_ongeki.time_beats',
                    epsilon=eps,
                    epsilon_source=eps_src,
                ))
            prev_m, prev_t, prev_tb, prev_idx = m, t, tb, idx

    return warns


def _tick_grid_consistency_checks(streams: Dict[str, List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    warns: List[Dict[str, Any]] = []
    cap, cap_src = _get_int_req('tick_grid_warning_cap', 50)
    cap_key = 'gating.phase4.timing_surface.requirements.tick_grid_warning_cap'
    base_key = 'gating.phase4.timing_surface'

    ticks_by_measure: Dict[int, List[int]] = {}
    for events in streams.values():
        for ev in events:
            m = safe_int(ev.get('measure'))
            t = safe_int(ev.get('tick'))
            if m is None or t is None or t < 0:
                continue
            ticks_by_measure.setdefault(m, []).append(t)

    if not ticks_by_measure:
        return warns

    global_g = 0
    for _m, ticks in ticks_by_measure.items():
        uniq = sorted(set(ticks))
        diffs = [b - a for a, b in zip(uniq, uniq[1:]) if (b - a) > 0]
        g = 0
        for d in diffs:
            g = math.gcd(g, int(d))
        if g > 0:
            global_g = math.gcd(global_g, g)

    if global_g <= 1:
        return warns

    for m, ticks in ticks_by_measure.items():
        for t in ticks:
            if t % global_g != 0:
                warns.append(_w(
                    code='O_TICK_GRID_INCONSISTENT',
                    schema_key=cap_key,
                    schema_keys=[cap_key, base_key],
                    message=f"tick value does not align to inferred grid (measure={m}, tick={t}, grid_step={global_g}).",
                    source='validator_ongeki.tick_grid',
                    grid_step=global_g,
                    warning_cap=cap,
                    warning_cap_source=cap_src,
                ))
                if len(warns) >= cap:
                    return warns

    return warns


def _timing_surface_checks(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    warns: List[Dict[str, Any]] = []

    sections = payload.get('sections')
    meta = payload.get('meta') if isinstance(payload.get('meta'), dict) else {}
    extra = payload.get('extra') if isinstance(payload.get('extra'), dict) else {}

    meta_bpm = meta.get('bpm')
    extra_bpms = extra.get('bpm_values')

    base_key = 'gating.phase4.timing_surface'

    if not isinstance(sections, list) or not sections:
        if _is_number(meta_bpm) and float(meta_bpm) > 0:
            warns.append(_w(
                code='O_SEC_TIMING_MISSING',
                schema_key=base_key,
                schema_keys=[base_key],
                message='meta.bpm is present but sections timing surface is missing.',
                source='validator_ongeki.timing_surface',
            ))
        if isinstance(extra_bpms, list) and any(_is_number(b) and float(b) > 0 for b in extra_bpms):
            warns.append(_w(
                code='O_SEC_TIMING_MISSING',
                schema_key=base_key,
                schema_keys=[base_key],
                message='extra.bpm_values is present but sections timing surface is missing.',
                source='validator_ongeki.timing_surface',
            ))
        return warns

    for i, sec in enumerate(sections):
        if not isinstance(sec, dict):
            warns.append(_w(
                code='O_SEC_INVALID',
                schema_key=base_key,
                schema_keys=[base_key],
                message=f'sections[{i}] must be an object/dict.',
                source='validator_ongeki.timing_surface',
            ))
            continue

        if sec.get('timing_surface_only') is True:
            bpm = sec.get('bpm')
            bpm_key = 'gating.phase4.timing_surface.requirements.timing_surface_only_requires_bpm'
            if not _is_number(bpm) or float(bpm) <= 0:
                warns.append(_w(
                    code='O_SEC_BPM_INVALID',
                    schema_key=bpm_key,
                    schema_keys=[bpm_key, base_key],
                    message=f'sections[{i}] timing_surface_only requires a positive bpm.',
                    source='validator_ongeki.timing_surface',
                ))

            forbid_key = 'gating.phase4.timing_surface.requirements.forbid_density_fields_when_timing_surface_only'
            for forbidden in ('npb', 'nps', 'section_coverage', 'coverage'):
                if forbidden in sec:
                    warns.append(_w(
                        code='O_SEC_TIMING_ONLY_HAS_DENSITY',
                        schema_key=forbid_key,
                        schema_keys=[forbid_key, base_key],
                        message=f"sections[{i}] timing_surface_only should not include '{forbidden}'.",
                        source='validator_ongeki.timing_surface',
                    ))

    streams = _iter_timing_event_streams(sections)
    warns.extend(_tick_checks(payload))
    warns.extend(_measure_negative_checks(streams))
    warns.extend(_time_beats_monotonicity_checks(streams))
    warns.extend(_tick_grid_consistency_checks(streams))
    return warns


class OngekiValidator(BaseValidatorV2):
    game_id = 'ongeki'

    def validate_row(self, canonical_row: Dict[str, Any]) -> ValidationResult:  # type: ignore
        if not isinstance(canonical_row, dict):
            return build_validation_fail(self.game_id, [{"code": "O_ROW_TYPE", "message": "canonical_row must be a dict."}])

        payload = canonical_row.get('canonical_payload')
        if not isinstance(payload, dict):
            if isinstance(canonical_row.get('game_id'), str) and 'canonical_payload' not in canonical_row:
                payload = canonical_row
            else:
                return build_validation_fail(self.game_id, [{"code": "O_PAYLOAD_MISSING", "message": "canonical_payload must be present and be a dict."}])

        warnings: List[Dict[str, Any]] = []
        diagnostics: Dict[str, Any] = {}

        warnings.extend(_timing_surface_checks(payload))

        thr, thr_src = _get_float_req('tick_ge_resolution_ratio_threshold', 0.05)
        cap, cap_src = _get_int_req('tick_grid_warning_cap', 50)
        eps, eps_src = _get_float_req('time_beats_monotonic_epsilon', 1e-9)
        diagnostics['tick_ge_resolution_ratio_threshold'] = thr
        diagnostics['tick_ge_resolution_ratio_threshold_source'] = thr_src
        diagnostics['tick_grid_warning_cap'] = cap
        diagnostics['tick_grid_warning_cap_source'] = cap_src
        diagnostics['time_beats_monotonic_epsilon'] = eps
        diagnostics['time_beats_monotonic_epsilon_source'] = eps_src

        diagnostics['has_sections'] = isinstance(payload.get('sections'), list) and bool(payload.get('sections'))
        diagnostics['source_format'] = payload.get('source_format')
        _req, _labels, _notes, req_src = _load_schema_context()
        diagnostics['schema_requirements_source'] = req_src

        return build_validation_ok(self.game_id, warnings=warnings, diagnostics=diagnostics)


__all__ = ['OngekiValidator']
