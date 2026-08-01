#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

"""
validator_ongeki.py (FULL REPLACEMENT - v2 normalized)

UMI Phase 3 validator for ONGEKI.

Scope (Phase 3 only):
- Structural validation of canonical rows / canonical payloads emitted by adapter_ongeki.py
- No gameplay semantics
- No tips / Phase 4 runtime decisions
- Conservative: prefer warnings over hard failures when data is partial

Schema-driven thresholds (policy knobs) are read from:
  ongeki.json -> gating.phase4.timing_surface.requirements

All structured warnings emitted by this validator include:
- schema_key
- schema_keys
- schema_key_labels
- schema_key_notes
- source

This is wiring / validation only; it does not modify completed phases.
"""

# ---------------------------------------------------------------------
# Standard library imports
# ---------------------------------------------------------------------
from typing import Any, Dict, List, Optional, Tuple
import math
import json
from pathlib import Path

# ---------------------------------------------------------------------
# Base validator v2
# ---------------------------------------------------------------------
from ..base_validator_v2 import BaseValidatorV2
from ..common_validator_utils import (
    safe_int,
    safe_float,
    build_validation_ok,
    build_validation_fail,
)

# ---------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------
GAME_ID = "ongeki"

# --------------------------------------------------
# Schema context (requirements + labels + full notes)
# --------------------------------------------------
_SCHEMA_CACHE: Dict[str, Tuple[Dict[str, Any], Dict[str, str], Dict[str, str], str]] = {}


def _fallback_label_from_schema_key(k: str) -> str:
    """Generate a human-readable label from a schema key path."""
    if not isinstance(k, str) or not k:
        return str(k)

    parts = k.split(".")

    if len(parts) >= 2 and parts[0] == "gating" and parts[1] == "phase4":
        phase = "Phase 4"
        if "timing_surface" in parts:
            if "requirements" in parts:
                tail = parts[parts.index("requirements") + 1 :]
                tail_txt = " ".join(t.replace("_", " ") for t in tail).strip()
                return f"{phase} timing surface requirement: {tail_txt}" if tail_txt else f"{phase} timing surface requirement"
            return f"{phase} timing surface gate"

        tail_txt = " ".join(t.replace("_", " ") for t in parts[2:]).strip()
        return f"{phase} gate: {tail_txt}" if tail_txt else f"{phase} gate"

    return parts[-1].replace("_", " ")


def _load_schema_context() -> Tuple[Dict[str, Any], Dict[str, str], Dict[str, str], str]:
    """
    Load schema requirements and derive labels + full notes.

    UNTRUNCATED labels:
    - If a note exists, labels[schema_key] == note (full text)
    - Otherwise labels[schema_key] == fallback label derived from schema_key
    """
    cache_key = "ongeki_schema_context"
    if cache_key in _SCHEMA_CACHE:
        return _SCHEMA_CACHE[cache_key]

    default_req: Dict[str, Any] = {
        "tick_ge_resolution_ratio_threshold": 0.05,
        "tick_grid_warning_cap": 50,
        "time_beats_monotonic_epsilon": 1e-9,
        "timing_surface_only_requires_bpm": True,
        "forbid_density_fields_when_timing_surface_only": True,
    }

    here = Path(__file__).resolve().parent
    candidates = [
        here / "ongeki.json",
        here / "analysis_schema.ongeki.v1.json",
        here / "schemas" / "ongeki.json",
        here / "schemas" / "analysis_schema.ongeki.v1.json",
        here / "analysis_schemas" / "ongeki.json",
        here / "analysis_schemas" / "analysis_schema.ongeki.v1.json",
        here.parent / "schemas" / "ongeki.json",
        here.parent / "schemas" / "analysis_schema.ongeki.v1.json",
    ]

    labels: Dict[str, str] = {"gating.phase4.timing_surface": "Phase 4 timing surface gate"}
    notes: Dict[str, str] = {}

    for p in candidates:
        try:
            if not p.exists():
                continue

            raw = json.loads(p.read_text(encoding="utf-8"))
            timing_surface = (((raw.get("gating") or {}).get("phase4") or {}).get("timing_surface") or {})
            req = timing_surface.get("requirements")

            if not isinstance(req, dict):
                continue

            merged = dict(default_req)
            merged.update(req)

            base_key = "gating.phase4.timing_surface"
            base_note = timing_surface.get("notes")
            if isinstance(base_note, str) and base_note.strip():
                notes[base_key] = base_note
                labels[base_key] = base_note
            else:
                labels[base_key] = _fallback_label_from_schema_key(base_key)

            for k in req.keys():
                if not isinstance(k, str) or k.endswith("_notes"):
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

    base_key = "gating.phase4.timing_surface"
    labels.setdefault(base_key, _fallback_label_from_schema_key(base_key))
    _SCHEMA_CACHE[cache_key] = (default_req, labels, notes, "default")
    return default_req, labels, notes, "default"


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
    return notes.get(k, "")


# ----------------------------
# Structured warning builder
# ----------------------------
def _w(
    *,
    code: str,
    schema_key: str,
    schema_keys: Optional[List[str]] = None,
    message: str,
    source: str,
    **extra: Any,
) -> Dict[str, Any]:
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
        "code": code,
        "schema_key": schema_key,
        "schema_keys": dedup,
        "schema_key_labels": labels,
        "schema_key_notes": full_notes,
        "message": message,
        "source": source,
    }
    out.update(extra)
    return out


# ----------------------------
# Helpers
# ----------------------------
def _err(code: str, message: str) -> str:
    return f"{code}: {message}"


def _is_number(x: Any) -> bool:
    return isinstance(x, (int, float)) and x == x


def _extract_resolution_from_sections(sections: Any) -> Optional[int]:
    if not isinstance(sections, list):
        return None
    for sec in sections:
        if isinstance(sec, dict) and sec.get("timing_surface_only") is True:
            rr = safe_int(sec.get("resolution"))
            if isinstance(rr, int) and rr > 0:
                return rr
    return None


def _iter_timing_event_streams(sections: Any) -> Dict[str, List[Dict[str, Any]]]:
    out: Dict[str, List[Dict[str, Any]]] = {
        "bpm_events": [],
        "meter_events": [],
        "soflan_events": [],
    }
    if not isinstance(sections, list):
        return out
    for sec in sections:
        if not isinstance(sec, dict):
            continue
        tp = sec.get("timing_positions")
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
    sections = payload.get("sections")
    streams = _iter_timing_event_streams(sections)
    all_events: List[Dict[str, Any]] = []
    for lst in streams.values():
        all_events.extend(lst)

    if not any(ev.get("tick") is not None for ev in all_events):
        return warns

    resolution = _extract_resolution_from_sections(sections)
    base_key = "gating.phase4.timing_surface"

    if resolution is None:
        warns.append(
            _w(
                code="O_RESOLUTION_MISSING_FOR_TICK",
                schema_key=base_key,
                schema_keys=[base_key],
                message="Timing events include 'tick' but no positive 'resolution' found in sections; cannot validate tick bounds.",
                source="validator_ongeki.tick_range",
            )
        )
        return warns

    tick_total = 0
    tick_ge = 0

    for i, ev in enumerate(all_events):
        t = safe_int(ev.get("tick"))
        if t is None:
            continue
        tick_total += 1
        if t < 0:
            warns.append(
                _w(
                    code="O_TICK_OUT_OF_RANGE",
                    schema_key=base_key,
                    schema_keys=[base_key],
                    message=f"Timing event #{i} has tick < 0 (tick={t}).",
                    source="validator_ongeki.tick_range",
                    resolution=resolution,
                )
            )
        elif t >= resolution:
            tick_ge += 1
            warns.append(
                _w(
                    code="O_TICK_OUT_OF_RANGE",
                    schema_key=base_key,
                    schema_keys=[base_key],
                    message=f"Timing event #{i} has tick >= resolution (tick={t}, resolution={resolution}).",
                    source="validator_ongeki.tick_range",
                    resolution=resolution,
                )
            )

    if tick_total > 0:
        ratio = float(tick_ge) / float(tick_total)
        thr, thr_src = _get_float_req("tick_ge_resolution_ratio_threshold", 0.05)
        thr_key = "gating.phase4.timing_surface.requirements.tick_ge_resolution_ratio_threshold"
        if ratio >= thr:
            warns.append(
                _w(
                    code="O_TICK_GE_RESOLUTION_RATIO",
                    schema_key=thr_key,
                    schema_keys=[thr_key, base_key],
                    message=(
                        f"High ratio of ticks >= resolution: {tick_ge}/{tick_total} ({ratio:.1%}) with resolution={resolution}. "
                        "This may indicate incorrect resolution inference or malformed measure/tick positions."
                    ),
                    source="validator_ongeki.tick_range",
                    resolution=resolution,
                    tick_total=tick_total,
                    tick_ge_resolution=tick_ge,
                    ratio=ratio,
                    threshold=thr,
                    threshold_source=thr_src,
                )
            )

    return warns


def _measure_negative_checks(streams: Dict[str, List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    warns: List[Dict[str, Any]] = []
    base_key = "gating.phase4.timing_surface"
    for stream, events in streams.items():
        for i, ev in enumerate(events):
            m = safe_int(ev.get("measure"))
            if m is not None and m < 0:
                warns.append(
                    _w(
                        code="O_MEASURE_NEGATIVE",
                        schema_key=base_key,
                        schema_keys=[base_key],
                        message=f"{stream} event #{i} has measure < 0 (measure={m}).",
                        source="validator_ongeki.measure",
                    )
                )
    return warns


def _time_beats_monotonicity_checks(streams: Dict[str, List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    warns: List[Dict[str, Any]] = []
    eps, eps_src = _get_float_req("time_beats_monotonic_epsilon", 1e-9)
    eps_key = "gating.phase4.timing_surface.requirements.time_beats_monotonic_epsilon"
    base_key = "gating.phase4.timing_surface"

    for stream, events in streams.items():
        sortable = []
        for idx, ev in enumerate(events):
            m = safe_int(ev.get("measure"))
            t = safe_int(ev.get("tick"))
            tb = ev.get("time_beats")
            if m is None or t is None or not _is_number(tb):
                continue
            sortable.append((m, t, float(tb), idx))
        if len(sortable) < 2:
            continue

        sortable.sort(key=lambda x: (x[0], x[1], x[3]))
        prev_m, prev_t, prev_tb, _prev_idx = sortable[0][0], sortable[0][1], sortable[0][2], sortable[0][3]

        for m, t, tb, idx in sortable[1:]:
            if tb + eps < prev_tb:
                warns.append(
                    _w(
                        code="O_TIME_BEATS_NON_MONOTONIC",
                        schema_key=eps_key,
                        schema_keys=[eps_key, base_key],
                        message=(
                            f"{stream} time_beats decreases at event #{idx} (measure={m}, tick={t}, time_beats={tb}) "
                            f"< previous (measure={prev_m}, tick={prev_t}, time_beats={prev_tb})."
                        ),
                        source="validator_ongeki.time_beats",
                        epsilon=eps,
                        epsilon_source=eps_src,
                    )
                )
            prev_m, prev_t, prev_tb = m, t, tb

    return warns


def _tick_grid_consistency_checks(streams: Dict[str, List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    warns: List[Dict[str, Any]] = []
    cap, cap_src = _get_int_req("tick_grid_warning_cap", 50)
    cap_key = "gating.phase4.timing_surface.requirements.tick_grid_warning_cap"
    base_key = "gating.phase4.timing_surface"

    ticks_by_measure: Dict[int, List[int]] = {}
    for events in streams.values():
        for ev in events:
            m = safe_int(ev.get("measure"))
            t = safe_int(ev.get("tick"))
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
                warns.append(
                    _w(
                        code="O_TICK_GRID_INCONSISTENT",
                        schema_key=cap_key,
                        schema_keys=[cap_key, base_key],
                        message=f"tick value does not align to inferred grid (measure={m}, tick={t}, grid_step={global_g}).",
                        source="validator_ongeki.tick_grid",
                        grid_step=global_g,
                        warning_cap=cap,
                        warning_cap_source=cap_src,
                    )
                )
                if len(warns) >= cap:
                    return warns

    return warns


def _timing_surface_checks(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    warns: List[Dict[str, Any]] = []

    sections = payload.get("sections")
    meta = payload.get("meta") if isinstance(payload.get("meta"), dict) else {}
    extra = payload.get("extra") if isinstance(payload.get("extra"), dict) else {}

    meta_bpm = meta.get("bpm")
    extra_bpms = extra.get("bpm_values")

    base_key = "gating.phase4.timing_surface"

    if not isinstance(sections, list) or not sections:
        if _is_number(meta_bpm) and float(meta_bpm) > 0:
            warns.append(
                _w(
                    code="O_SEC_TIMING_MISSING",
                    schema_key=base_key,
                    schema_keys=[base_key],
                    message="meta.bpm is present but sections timing surface is missing.",
                    source="validator_ongeki.timing_surface",
                )
            )
        if isinstance(extra_bpms, list) and any(_is_number(b) and float(b) > 0 for b in extra_bpms):
            warns.append(
                _w(
                    code="O_SEC_TIMING_MISSING",
                    schema_key=base_key,
                    schema_keys=[base_key],
                    message="extra.bpm_values is present but sections timing surface is missing.",
                    source="validator_ongeki.timing_surface",
                )
            )
        return warns

    for i, sec in enumerate(sections):
        if not isinstance(sec, dict):
            warns.append(
                _w(
                    code="O_SEC_INVALID",
                    schema_key=base_key,
                    schema_keys=[base_key],
                    message=f"sections[{i}] must be an object/dict.",
                    source="validator_ongeki.timing_surface",
                )
            )
            continue

        if sec.get("timing_surface_only") is True:
            bpm = sec.get("bpm")
            bpm_key = "gating.phase4.timing_surface.requirements.timing_surface_only_requires_bpm"
            if not _is_number(bpm) or float(bpm) <= 0:
                warns.append(
                    _w(
                        code="O_SEC_BPM_INVALID",
                        schema_key=bpm_key,
                        schema_keys=[bpm_key, base_key],
                        message=f"sections[{i}] timing_surface_only requires a positive bpm.",
                        source="validator_ongeki.timing_surface",
                    )
                )

            forbid_key = "gating.phase4.timing_surface.requirements.forbid_density_fields_when_timing_surface_only"
            for forbidden in ("npb", "nps", "section_coverage", "coverage"):
                if forbidden in sec:
                    warns.append(
                        _w(
                            code="O_SEC_TIMING_ONLY_HAS_DENSITY",
                            schema_key=forbid_key,
                            schema_keys=[forbid_key, base_key],
                            message=f"sections[{i}] timing_surface_only should not include '{forbidden}'.",
                            source="validator_ongeki.timing_surface",
                        )
                    )

    streams = _iter_timing_event_streams(sections)
    warns.extend(_tick_checks(payload))
    warns.extend(_measure_negative_checks(streams))
    warns.extend(_time_beats_monotonicity_checks(streams))
    warns.extend(_tick_grid_consistency_checks(streams))
    return warns


# --------------------------------------------------
# Result helpers
# --------------------------------------------------
def _to_warning_strings(structured_warnings: List[Dict[str, Any]]) -> List[str]:
    out: List[str] = []
    for w in structured_warnings:
        if not isinstance(w, dict):
            continue
        code = w.get("code") or "O_WARN"
        msg = w.get("message") or ""
        out.append(f"{code}: {msg}")
    return out


def _finalize_ok(
    *,
    structured_warnings: List[Dict[str, Any]],
    diagnostics: Dict[str, Any],
    degraded_mode: bool = False,
) -> Dict[str, Any]:
    result = build_validation_ok(
        warnings=_to_warning_strings(structured_warnings),
        degraded_mode=degraded_mode,
    )
    result["game_id"] = GAME_ID
    result["validator_id"] = "validator_ongeki"
    result["diagnostics"] = diagnostics
    result["structured_warnings"] = structured_warnings
    result["structured_errors"] = []
    return result


def _finalize_fail(
    *,
    errors: List[str],
    structured_warnings: List[Dict[str, Any]],
    diagnostics: Dict[str, Any],
    degraded_mode: bool = False,
) -> Dict[str, Any]:
    result = build_validation_fail(
        errors=errors,
        warnings=_to_warning_strings(structured_warnings),
        degraded_mode=degraded_mode,
    )
    result["game_id"] = GAME_ID
    result["validator_id"] = "validator_ongeki"
    result["diagnostics"] = diagnostics
    result["structured_warnings"] = structured_warnings
    result["structured_errors"] = errors
    return result


# ---------------------------------------------------------------------
# Validator implementation
# ---------------------------------------------------------------------
class OngekiValidator(BaseValidatorV2):
    game_id = GAME_ID
    validator_id = "validator_ongeki"

    def validate_v2(
        self,
        payload: Dict[str, Any],
        *,
        canonical_payload: Optional[Dict[str, Any]] = None,
        canonical_row: Optional[Dict[str, Any]] = None,
        **context: Any,
    ) -> ValidationResult:
        errors: List[str] = []
        structured_warnings: List[Dict[str, Any]] = []
        diagnostics: Dict[str, Any] = {}

        canonical_payload, canonical_row, input_kind = self.coerce_payload_and_row(
            payload,
            canonical_payload=canonical_payload,
            canonical_row=canonical_row,
        )
        diagnostics["input_kind"] = input_kind

        resolved = self.resolve_identity_fields(
            canonical_payload,
            canonical_row,
        )
        diagnostics["resolved_game"] = resolved["game"]
        diagnostics["resolved_chart_id"] = resolved["chart_id"]
        diagnostics["resolved_title"] = resolved["title"]
        diagnostics["resolved_difficulty"] = resolved["difficulty"]

        # --------------------------------------------------
        # Identity
        # --------------------------------------------------
        if not resolved["game"]:
            errors.append(_err("O0_GAME_MISSING", "missing required field: game"))

        if not resolved["chart_id"]:
            errors.append(_err("O0_CHART_ID_MISSING", "missing required field: chart_id"))

        if not resolved["difficulty"]:
            errors.append(_err("O0_DIFFICULTY_MISSING", "missing required field: difficulty"))

        if not resolved["title"]:
            structured_warnings.append(
                _w(
                    code="O0_TITLE_MISSING",
                    schema_key="gating.phase4.timing_surface",
                    schema_keys=["gating.phase4.timing_surface"],
                    message="title is missing",
                    source="validator_ongeki.identity",
                )
            )

        if resolved["game"] and resolved["game"] != self.game_id:
            errors.append(_err("O0_GAME_MISMATCH", f"game must be '{self.game_id}', got {resolved['game']!r}"))

        # --------------------------------------------------
        # Row-level sanity
        # --------------------------------------------------
        if isinstance(canonical_row, dict) and canonical_row:
            row_game = canonical_row.get("game_id", canonical_row.get("game"))
            if row_game is not None and row_game != self.game_id:
                errors.append(
                    _err(
                        "O0_ROW_GAME_MISMATCH",
                        f"canonical_row game must be '{self.game_id}', got {row_game!r}",
                    )
                )

            ntc = canonical_row.get("note_total_chart")
            if ntc is not None:
                ntc_int = safe_int(ntc, default=None)
                if ntc_int is None or ntc_int < 0:
                    errors.append(
                        _err(
                            "O0_ROW_NOTE_TOTAL_INVALID",
                            f"canonical_row['note_total_chart'] must be a non-negative int, got {ntc!r}",
                        )
                    )

        # --------------------------------------------------
        # Payload structure
        # --------------------------------------------------
        note_events = canonical_payload.get("note_events")
        if not isinstance(note_events, list):
            errors.append(_err("O1_NOTE_EVENTS_TYPE", "canonical_payload['note_events'] must be a list"))
            note_events = []

        chart_meta = canonical_payload.get("chart_meta")
        if not isinstance(chart_meta, dict):
            errors.append(_err("O1_CHART_META_TYPE", "canonical_payload['chart_meta'] must be a dict"))
            chart_meta = {}

        diagnostics["note_events_present"] = isinstance(canonical_payload.get("note_events"), list)
        diagnostics["chart_meta_present"] = isinstance(canonical_payload.get("chart_meta"), dict)

        # --------------------------------------------------
        # Optional note_events sanity (conservative)
        # --------------------------------------------------
        prev_tb = -1.0
        for idx, ev in enumerate(note_events):
            if not isinstance(ev, dict):
                errors.append(_err("O1_EVENT_TYPE", f"note_events[{idx}] must be dict"))
                continue

            tb = safe_float(ev.get("time_beats"), default=None)
            lane = safe_int(ev.get("lane"), default=None)

            if tb is None:
                errors.append(_err("O1_TIME_TYPE", f"note_events[{idx}].time_beats must be numeric"))
            else:
                if tb < 0:
                    errors.append(_err("O1_TIME_NEGATIVE", f"note_events[{idx}].time_beats must be >= 0"))
                if tb + 1e-9 < prev_tb:
                    errors.append(
                        _err(
                            "O1_TIME_MONOTONIC",
                            f"note_events[{idx}].time_beats={tb} is less than previous time_beats={prev_tb}",
                        )
                    )
                prev_tb = tb

            # ONGEKI lane model can be partially abstracted in route-only mode,
            # so only reject obviously invalid negative lanes
            if lane is not None and lane < 0:
                errors.append(_err("O1_LANE_INVALID", f"note_events[{idx}].lane must be >= 0"))

            kind = ev.get("kind")
            if kind is not None and not isinstance(kind, str):
                errors.append(_err("O1_KIND_TYPE", f"note_events[{idx}].kind must be str when present"))

        # --------------------------------------------------
        # Timing-surface checks (warning-driven by policy)
        # --------------------------------------------------
        structured_warnings.extend(_timing_surface_checks(canonical_payload))

        # --------------------------------------------------
        # Mild BPM sanity (warning only)
        # --------------------------------------------------
        bpm = safe_float(chart_meta.get("bpm"), default=None)
        if bpm is None or bpm <= 0:
            structured_warnings.append(
                _w(
                    code="O1_BPM_MISSING",
                    schema_key="gating.phase4.timing_surface",
                    schema_keys=["gating.phase4.timing_surface"],
                    message="chart_meta.bpm is missing or non-positive",
                    source="validator_ongeki.chart_meta",
                )
            )

        max_time_beats = safe_float(chart_meta.get("max_time_beats"), default=None)
        if max_time_beats is not None and max_time_beats < 0:
            errors.append(_err("O1_MAX_TIME_INVALID", "chart_meta.max_time_beats must be >= 0"))

        diagnostics["note_event_count"] = len(note_events)
        diagnostics["row_shape_present"] = bool(canonical_row)

        degraded_mode = bool(structured_warnings)

        if errors:
            return _finalize_fail(
                errors=errors,
                structured_warnings=structured_warnings,
                diagnostics=diagnostics,
                degraded_mode=degraded_mode,
            )

        return _finalize_ok(
            structured_warnings=structured_warnings,
            diagnostics=diagnostics,
            degraded_mode=degraded_mode,
        )

    def validate_row(self, canonical_row: Dict[str, Any]) -> dict:
        return self.validate(canonical_row)

    def capabilities(self) -> dict:
        return {
            "note_model": "lane_based",
            "supports_sections": True,
            "supports_variable_bpm": True,
            "supports_timing_surface_schema": True,
            "structured_warnings": True,
            "timing_surface_policy_driven": True,
        }


__all__ = ["OngekiValidator"]