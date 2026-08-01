#!/usr/bin/env python3
from __future__ import annotations

"""
validator_yumesute.py

UMI Phase 3 validator for yumesute.

Responsibilities:
- structural validation only
- no mutation / no enrichment
- no gameplay inference
- local validation only (not verification)

Aligned with:
- BaseValidatorV2
- canonical payload contract
- Wave-by-game normalization strategy
"""

from typing import Any, Dict, List, Optional, Tuple

from ..base_validator_v2 import BaseValidatorV2
from ..common_validator_utils import safe_int, safe_float


GAME_ID = "yumesute"
CANONICAL_KINDS = {"tap", "hold_path", "slide", "flick"}

# Soft numeric tolerance for monotonic checks
_EPS = 1e-9

# Fallback lane bounds if chart_meta does not specify and inference is impossible
DEFAULT_LANE_MIN = 0
DEFAULT_LANE_MAX = 7

# Safety cap for absurd inferred spans
_MAX_REASONABLE_LANE_SPAN = 32


def _err(code: str, message: str) -> str:
    return f"{code}: {message}"


def _warn(code: str, message: str) -> str:
    return f"{code}: {message}"


def _is_number(x: Any) -> bool:
    return isinstance(x, (int, float)) and x == x


def _lane_bounds_from_chart_meta(
    chart_meta: Dict[str, Any],
    note_events: List[Dict[str, Any]],
) -> Tuple[int, int, str, List[str]]:
    """
    Determine usable lane bounds from chart_meta or infer from note_events.

    Returns:
        (lane_min, lane_max, source_label, warnings)
    """
    warnings: List[str] = []

    # 1) explicit lane_min / lane_max
    lane_min = safe_int(chart_meta.get("lane_min"), default=None)
    lane_max = safe_int(chart_meta.get("lane_max"), default=None)
    if lane_min is not None and lane_max is not None and lane_min <= lane_max:
        return lane_min, lane_max, "chart_meta.lane_min/lane_max", warnings

    # 2) lane_count aliases
    for key in ("lane_count", "num_lanes", "stage_lanes", "lane_total"):
        lane_count = safe_int(chart_meta.get(key), default=None)
        if lane_count is not None and lane_count > 0:
            return 0, lane_count - 1, f"chart_meta.{key}", warnings

    # 3) lanes list
    lanes = chart_meta.get("lanes")
    if isinstance(lanes, (list, tuple)) and len(lanes) > 0:
        return 0, len(lanes) - 1, "chart_meta.lanes", warnings

    # 4) infer from note_events
    observed: List[int] = []
    for ev in note_events:
        if not isinstance(ev, dict):
            continue
        li = safe_int(ev.get("lane"), default=None)
        if li is not None:
            observed.append(li)

    if observed:
        mn, mx = min(observed), max(observed)
        if mx - mn > _MAX_REASONABLE_LANE_SPAN:
            warnings.append(
                _warn(
                    "Y2_LANE_BOUNDS_SUSPECT",
                    f"Inferred lane span too large ({mn}..{mx}); falling back to defaults {DEFAULT_LANE_MIN}..{DEFAULT_LANE_MAX}.",
                )
            )
            return DEFAULT_LANE_MIN, DEFAULT_LANE_MAX, "default", warnings
        return mn, mx, "inferred(note_events)", warnings

    # 5) hard fallback
    return DEFAULT_LANE_MIN, DEFAULT_LANE_MAX, "default", warnings


def _is_valid_lane(lane: Optional[int], lane_min: int, lane_max: int) -> bool:
    return lane is not None and lane_min <= lane <= lane_max


class YumesuteValidator(BaseValidatorV2):
    game_id = "yumesute"
    validator_id = "validator_yumesute"

    def validate_v2(
        self,
        payload: Dict[str, Any],
        *,
        canonical_payload: Optional[Dict[str, Any]] = None,
        canonical_row: Optional[Dict[str, Any]] = None,
        **context: Any,
    ) -> dict:
        errors: List[str] = []
        warnings: List[str] = []
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
        # Identity (STRICT)
        # --------------------------------------------------
        if not resolved["game"]:
            errors.append(_err("Y0_GAME_MISSING", "missing required field: game"))

        if not resolved["chart_id"]:
            errors.append(_err("Y0_CHART_ID_MISSING", "missing required field: chart_id"))

        if not resolved["difficulty"]:
            errors.append(_err("Y0_DIFFICULTY_MISSING", "missing required field: difficulty"))

        if not resolved["title"]:
            warnings.append(_warn("Y0_TITLE_MISSING", "missing title"))

        if resolved["game"] and resolved["game"] != self.game_id:
            errors.append(
                _err(
                    "Y0_GAME_MISMATCH",
                    f"game must be '{self.game_id}', got {resolved['game']!r}",
                )
            )

        # --------------------------------------------------
        # Row-level sanity (soft + identity consistency)
        # --------------------------------------------------
        if isinstance(canonical_row, dict) and canonical_row:
            row_game = canonical_row.get("game_id", canonical_row.get("game"))
            if row_game is not None and row_game != self.game_id:
                errors.append(
                    _err(
                        "Y0_ROW_GAME_MISMATCH",
                        f"canonical_row game must be '{self.game_id}', got {row_game!r}",
                    )
                )

            ntc = canonical_row.get("note_total_chart")
            if ntc is not None:
                ntc_int = safe_int(ntc, default=None)
                if ntc_int is None or ntc_int < 0:
                    errors.append(
                        _err(
                            "Y0_ROW_NOTE_TOTAL_INVALID",
                            f"canonical_row['note_total_chart'] must be a non-negative int, got {ntc!r}",
                        )
                    )

        # --------------------------------------------------
        # Payload structure
        # --------------------------------------------------
        note_events = canonical_payload.get("note_events")
        if not isinstance(note_events, list):
            errors.append(_err("Y1_NOTE_EVENTS_TYPE", "canonical_payload['note_events'] must be a list"))
            note_events = []

        chart_meta = canonical_payload.get("chart_meta")
        if not isinstance(chart_meta, dict):
            errors.append(_err("Y1_CHART_META_TYPE", "canonical_payload['chart_meta'] must be a dict"))
            chart_meta = {}

        diagnostics["note_events_present"] = isinstance(canonical_payload.get("note_events"), list)
        diagnostics["chart_meta_present"] = isinstance(canonical_payload.get("chart_meta"), dict)

        # --------------------------------------------------
        # BPM / duration sanity (soft-strict hybrid)
        # --------------------------------------------------
        bpm = safe_float(chart_meta.get("bpm"), default=None)
        if bpm is None or bpm <= 0:
            warnings.append(_warn("Y1_BPM_MISSING", "chart_meta.bpm is missing or non-positive"))

        max_time_beats = safe_float(chart_meta.get("max_time_beats"), default=None)
        if max_time_beats is None:
            warnings.append(_warn("Y1_MAX_TIME_MISSING", "chart_meta.max_time_beats missing"))
        elif max_time_beats < 0:
            errors.append(_err("Y1_MAX_TIME_INVALID", "chart_meta.max_time_beats must be >= 0"))

        # --------------------------------------------------
        # Lane bounds
        # --------------------------------------------------
        lane_min, lane_max, lane_source, lane_warnings = _lane_bounds_from_chart_meta(
            chart_meta,
            note_events,
        )
        warnings.extend(lane_warnings)

        diagnostics["lane_bounds"] = {
            "lane_min": lane_min,
            "lane_max": lane_max,
            "source": lane_source,
        }

        # --------------------------------------------------
        # Note events validation
        # --------------------------------------------------
        prev_t: float = -1.0

        for idx, ev in enumerate(note_events):
            if not isinstance(ev, dict):
                errors.append(_err("Y2_EVENT_TYPE", f"note_events[{idx}] must be dict"))
                continue

            tb = safe_float(ev.get("time_beats"), default=None)
            lane = safe_int(ev.get("lane"), default=None)
            kind = ev.get("kind")
            extra = ev.get("extra")

            # time_beats
            if tb is None:
                errors.append(_err("Y2_TIME_TYPE", f"note_events[{idx}].time_beats must be numeric"))
            else:
                if tb < 0:
                    errors.append(_err("Y2_TIME_NEGATIVE", f"note_events[{idx}].time_beats must be >= 0"))
                if tb + _EPS < prev_t:
                    errors.append(
                        _err(
                            "Y2_TIME_MONOTONIC",
                            f"note_events[{idx}].time_beats={tb} is less than previous time_beats={prev_t}",
                        )
                    )
                prev_t = tb

            # lane
            if lane is None:
                errors.append(_err("Y2_LANE_TYPE", f"note_events[{idx}].lane must be int"))
            elif not _is_valid_lane(lane, lane_min, lane_max):
                errors.append(
                    _err(
                        "Y2_LANE_RANGE",
                        f"note_events[{idx}].lane={lane} outside valid bounds {lane_min}..{lane_max}",
                    )
                )

            # kind
            if not isinstance(kind, str):
                errors.append(_err("Y1_KIND_TYPE", f"note_events[{idx}].kind must be str"))
            elif kind not in CANONICAL_KINDS:
                errors.append(
                    _err(
                        "Y1_KIND_INVALID",
                        f"note_events[{idx}].kind={kind!r} not allowed (expected one of {sorted(CANONICAL_KINDS)})",
                    )
                )

            # extra
            if extra is None:
                warnings.append(_warn("Y1_EXTRA_MISSING", f"note_events[{idx}].extra missing"))
                extra = {}
            elif not isinstance(extra, dict):
                errors.append(_err("Y1_EXTRA_TYPE", f"note_events[{idx}].extra must be dict"))
                continue

            # light structural expectations by kind
            if kind == "hold_path":
                duration_beats = safe_float(extra.get("duration_beats"), default=None)
                duration_raw = safe_int(extra.get("duration_raw"), default=None)
                if duration_beats is None and duration_raw is None:
                    warnings.append(
                        _warn(
                            "Y2_HOLD_DURATION_MISSING",
                            f"note_events[{idx}] kind='hold_path' missing duration_beats/duration_raw",
                        )
                    )

            if kind == "flick":
                if "raw_type" not in extra and "direction" not in extra:
                    warnings.append(
                        _warn(
                            "Y2_FLICK_SHAPE_MISSING",
                            f"note_events[{idx}] kind='flick' missing raw_type/direction in extra",
                        )
                    )

        # --------------------------------------------------
        # Soft parity (row vs payload)
        # --------------------------------------------------
        ntc = canonical_row.get("note_total_chart") if isinstance(canonical_row, dict) else None
        ntc_int = safe_int(ntc, default=None)
        if ntc_int is not None:
            if abs(len(note_events) - ntc_int) > max(50, int(0.2 * max(1, ntc_int))):
                warnings.append(
                    _warn(
                        "Y2_NOTE_TOTAL_MISMATCH",
                        f"note_total_chart mismatch is large: row={ntc_int}, payload_count={len(note_events)}",
                    )
                )

        # --------------------------------------------------
        # Final result
        # --------------------------------------------------
        diagnostics["note_event_count"] = len(note_events)
        diagnostics["row_shape_present"] = bool(canonical_row)

        if errors:
            return self.fail_result(
                errors=errors,
                warnings=warnings,
                degraded_mode=bool(warnings),
                diagnostics=diagnostics,
            )

        return self.ok_result(
            warnings=warnings,
            degraded_mode=bool(warnings),
            diagnostics=diagnostics,
        )

    def validate_row(self, canonical_row: Dict[str, Any]) -> dict:
        return self.validate(canonical_row)

    def capabilities(self) -> dict:
        return {
            "note_model": "lane_based",
            "supports_sections": True,
            "supports_variable_bpm": True,
            "supports_slides": True,
            "supports_flicks": True,
        }


__all__ = ["YumesuteValidator"]