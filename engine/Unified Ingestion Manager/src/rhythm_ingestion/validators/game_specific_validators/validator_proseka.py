#!/usr/bin/env python3
from __future__ import annotations

"""
validator_proseka.py

UMI Phase 3 validator for Project SEKAI ("proseka").

Responsibilities:
- canonical_row sanity
- canonical_payload.note_events structural integrity
- combo parity between note_events, row fields, and adapter_metadata
- optional sections sanity checks
- strict DB-backed combo consistency (MAX_DB_NOTE_DELTA = 0)

This validator is Phase-3 wiring only:
- no gameplay semantics inference
- no payload mutation
- no Phase 4 logic
"""

from typing import Any, Dict, List, Optional

from ..base_validator_v2 import BaseValidatorV2
from ..common_validator_utils import (
    safe_int,
    safe_float,
    compute_delta,
    is_within_threshold,
)


# ---------------------------------------------------------------------
# Constants (must remain aligned with adapter output)
# ---------------------------------------------------------------------

# Allowed raw_type values emitted by adapter_proseka
PROSEKA_RAW_TYPES: Dict[str, str] = {
    # Basic taps
    "tap": "TAP",
    "tap_critical": "TAP_CRITICAL",
    # Long / hold notes
    "hold_start": "HOLD_START",
    "hold_start_critical": "HOLD_START_CRITICAL",
    "hold_end": "HOLD_END",
    "hold_end_critical": "HOLD_END_CRITICAL",
    "hold_tick": "HOLD_TICK",
    "hold_tick_critical": "HOLD_TICK_CRITICAL",
    # Visual hold body segments
    "hold_body_segment": "HOLD_BODY_SEGMENT",
    # Trace notes
    "trace_body_segment": "TRACE_BODY_SEGMENT",
    "trace_tick": "TRACE_TICK",
    "trace_tick_critical": "TRACE_TICK_CRITICAL",
    # Trace flicks
    "trace_flick": "TRACE_FLICK",
    "trace_flick_critical": "TRACE_FLICK_CRITICAL",
    # Independent flicks
    "flick": "FLICK",
    "flick_critical": "FLICK_CRITICAL",
}

# Subset of raw types that contribute to combo
COMBO_RAW_TYPES = {
    "tap",
    "tap_critical",
    "hold_start",
    "hold_start_critical",
    "hold_end",
    "hold_end_critical",
    "hold_tick",
    "hold_tick_critical",
    "trace_tick",
    "trace_tick_critical",
    "flick",
    "flick_critical",
    "trace_flick",
    "trace_flick_critical",
}

# Strict DB-backed consistency for Proseka
MAX_DB_NOTE_DELTA = 0

# Canonical kinds allowed by canonical chart payload contract
CANONICAL_KINDS = {
    "tap",
    "critical_tap",
    "flick",
    "flick_arrow",
    "hold_body_or_start",
    "hold_path",
    "critical_hold_path",
}

# Small monotonic tolerance
_EPS = 1e-9


def _err(code: str, message: str) -> str:
    return f"{code}: {message}"


def _warn(code: str, message: str) -> str:
    return f"{code}: {message}"


def _compute_combo_from_note_events(note_events: List[Dict[str, Any]]) -> int:
    combo = 0
    for ev in note_events:
        if not isinstance(ev, dict):
            continue
        extra = ev.get("extra")
        if not isinstance(extra, dict):
            continue
        raw_type = extra.get("raw_type")
        if isinstance(raw_type, str) and raw_type in COMBO_RAW_TYPES:
            combo += 1
    return combo


class ProsekaValidator(BaseValidatorV2):
    game_id = "proseka"
    validator_id = "validator_proseka"

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
            errors.append(_err("P0_GAME_MISSING", "missing required field: game"))

        if not resolved["chart_id"]:
            errors.append(_err("P0_CHART_ID_MISSING", "missing required field: chart_id"))

        if not resolved["difficulty"]:
            errors.append(_err("P0_DIFFICULTY_MISSING", "missing required field: difficulty"))

        # title is useful, but can degrade gracefully if path-based fallback is incomplete
        if not resolved["title"]:
            warnings.append(_warn("P0_TITLE_MISSING", "missing title"))

        if resolved["game"] and resolved["game"] != self.game_id:
            errors.append(
                _err(
                    "P0_GAME_MISMATCH",
                    f"game must be '{self.game_id}', got {resolved['game']!r}",
                )
            )

        # --------------------------------------------------
        # Row-level sanity
        # --------------------------------------------------
        if isinstance(canonical_row, dict) and canonical_row:
            row_game = canonical_row.get("game_id", canonical_row.get("game"))
            if row_game is not None and row_game != self.game_id:
                errors.append(
                    _err(
                        "P0_ROW_GAME_MISMATCH",
                        f"canonical_row game must be '{self.game_id}', got {row_game!r}",
                    )
                )

            ntc = canonical_row.get("note_total_chart")
            if ntc is not None:
                ntc_int = safe_int(ntc, default=None)
                if ntc_int is None or ntc_int < 0:
                    errors.append(
                        _err(
                            "P0_ROW_NOTE_TOTAL_INVALID",
                            f"canonical_row['note_total_chart'] must be a non-negative int, got {ntc!r}",
                        )
                    )

        # --------------------------------------------------
        # Payload structure
        # --------------------------------------------------
        note_events = canonical_payload.get("note_events")
        if not isinstance(note_events, list):
            errors.append(_err("P1_NOTE_EVENTS_TYPE", "canonical_payload['note_events'] must be a list"))
            note_events = []

        chart_meta = canonical_payload.get("chart_meta")
        if not isinstance(chart_meta, dict):
            errors.append(_err("P1_CHART_META_TYPE", "canonical_payload['chart_meta'] must be a dict"))
            chart_meta = {}

        diagnostics["note_events_present"] = isinstance(canonical_payload.get("note_events"), list)
        diagnostics["chart_meta_present"] = isinstance(canonical_payload.get("chart_meta"), dict)

        # --------------------------------------------------
        # BPM / duration sanity
        # --------------------------------------------------
        bpm = safe_float(chart_meta.get("bpm"), default=None)
        if bpm is None or bpm <= 0:
            warnings.append(_warn("P1_BPM_MISSING", "chart_meta.bpm is missing or non-positive"))

        max_time_beats = safe_float(chart_meta.get("max_time_beats"), default=None)
        if max_time_beats is None:
            warnings.append(_warn("P1_MAX_TIME_MISSING", "chart_meta.max_time_beats missing"))
        elif max_time_beats < 0:
            errors.append(_err("P1_MAX_TIME_INVALID", "chart_meta.max_time_beats must be >= 0"))

        # --------------------------------------------------
        # Note events validation
        # --------------------------------------------------
        prev_t: float = -1.0

        for idx, ev in enumerate(note_events):
            if not isinstance(ev, dict):
                errors.append(_err("P1_EVENT_TYPE", f"note_events[{idx}] must be dict"))
                continue

            tb = safe_float(ev.get("time_beats"), default=None)
            lane = safe_int(ev.get("lane"), default=None)
            kind = ev.get("kind")
            extra = ev.get("extra")

            # time_beats
            if tb is None:
                errors.append(_err("P1_TIME_TYPE", f"note_events[{idx}].time_beats must be numeric"))
            else:
                if tb < 0:
                    errors.append(_err("P1_TIME_NEGATIVE", f"note_events[{idx}].time_beats must be >= 0"))
                if tb + _EPS < prev_t:
                    errors.append(
                        _err(
                            "P1_TIME_MONOTONIC",
                            f"note_events[{idx}].time_beats={tb} is less than previous time_beats={prev_t}",
                        )
                    )
                prev_t = tb

            # lane
            # canonical payload schema allows adapter-chosen convention; accept lane >= 0
            if lane is None:
                errors.append(_err("P1_LANE_TYPE", f"note_events[{idx}].lane must be int"))
            elif lane < 0:
                errors.append(_err("P1_LANE_INVALID", f"note_events[{idx}].lane must be >= 0"))

            # kind
            if not isinstance(kind, str):
                errors.append(_err("P1_KIND_TYPE", f"note_events[{idx}].kind must be str"))
            elif kind not in CANONICAL_KINDS:
                errors.append(
                    _err(
                        "P1_KIND_INVALID",
                        f"note_events[{idx}].kind={kind!r} not allowed (expected one of {sorted(CANONICAL_KINDS)})",
                    )
                )

            # extra
            if not isinstance(extra, dict):
                errors.append(_err("P1_EXTRA_TYPE", f"note_events[{idx}].extra must be dict"))
                continue

            raw_type = extra.get("raw_type")
            if not isinstance(raw_type, str):
                errors.append(_err("P1_RAW_TYPE_MISSING", f"note_events[{idx}].extra.raw_type must be str"))
                continue

            if raw_type not in PROSEKA_RAW_TYPES:
                errors.append(
                    _err(
                        "P1_RAW_TYPE_INVALID",
                        f"note_events[{idx}].extra.raw_type={raw_type!r} not in allowed raw types",
                    )
                )

            # --------------------------------------------------
            # Canonical kind vs raw_type consistency
            # --------------------------------------------------
            if kind == "critical_tap" and raw_type != "tap_critical":
                errors.append(
                    _err(
                        "P2_CRITICAL_TAP_MAPPING",
                        f"critical_tap must map to raw_type 'tap_critical', got {raw_type!r}",
                    )
                )

            if kind == "tap" and raw_type not in {"tap"}:
                # Some adapters may choose to collapse more raw types to tap in degraded mode,
                # so keep this as a warning rather than a hard fail.
                warnings.append(
                    _warn(
                        "P2_TAP_MAPPING_SOFT",
                        f"tap typically maps to raw_type 'tap', got {raw_type!r}",
                    )
                )

            if kind == "hold_body_or_start" and raw_type not in {
                "hold_start",
                "hold_end",
                "hold_tick",
                "trace_tick",
            }:
                errors.append(
                    _err(
                        "P2_HOLD_BODY_OR_START_MAPPING",
                        f"hold_body_or_start has invalid raw_type {raw_type!r}",
                    )
                )

            if kind == "critical_hold_path" and raw_type not in {
                "hold_start_critical",
                "hold_end_critical",
                "hold_tick_critical",
                "trace_tick_critical",
            }:
                errors.append(
                    _err(
                        "P2_CRITICAL_HOLD_MAPPING",
                        f"critical_hold_path has invalid raw_type {raw_type!r}",
                    )
                )

            if kind == "hold_path" and raw_type not in {
                "hold_body_segment",
                "trace_body_segment",
            }:
                errors.append(
                    _err(
                        "P2_HOLD_PATH_MAPPING",
                        f"hold_path has invalid raw_type {raw_type!r}",
                    )
                )

            if kind in {"flick", "flick_arrow"} and raw_type not in {
                "flick",
                "flick_critical",
                "trace_flick",
                "trace_flick_critical",
            }:
                errors.append(
                    _err(
                        "P2_FLICK_MAPPING",
                        f"{kind} has invalid raw_type {raw_type!r}",
                    )
                )

        # --------------------------------------------------
        # Sections sanity (optional, only when provided)
        # --------------------------------------------------
        sections = canonical_payload.get("sections")
        if sections is not None:
            if not isinstance(sections, list):
                errors.append(_err("P3_SECTIONS_TYPE", "canonical_payload['sections'] must be a list when present"))
            else:
                for idx, section in enumerate(sections):
                    if not isinstance(section, dict):
                        errors.append(_err("P3_SECTION_ITEM_TYPE", f"sections[{idx}] must be dict"))
                        continue

                    npb = safe_float(section.get("npb"), default=None)
                    nps = safe_float(section.get("nps"), default=None)
                    if npb is not None and npb < 0:
                        errors.append(_err("P3_SECTION_NPB_INVALID", f"sections[{idx}].npb must be >= 0"))
                    if nps is not None and nps < 0:
                        errors.append(_err("P3_SECTION_NPS_INVALID", f"sections[{idx}].nps must be >= 0"))

        # --------------------------------------------------
        # Combo parity
        # --------------------------------------------------
        combo_from_events = _compute_combo_from_note_events(note_events)
        diagnostics["combo_from_events"] = combo_from_events

        row_note_total_chart = None
        if isinstance(canonical_row, dict):
            row_note_total_chart = safe_int(canonical_row.get("note_total_chart"), default=None)

        if row_note_total_chart is not None:
            # Row vs payload parity is soft-warning only
            delta = compute_delta(combo_from_events, row_note_total_chart)
            diagnostics["row_combo_delta"] = delta
            if delta is not None and not is_within_threshold(delta, max(50, int(0.2 * max(1, row_note_total_chart)))):
                warnings.append(
                    _warn(
                        "P4_ROW_PAYLOAD_COMBO_MISMATCH",
                        f"row note_total_chart mismatch is large: row={row_note_total_chart}, payload_combo={combo_from_events}",
                    )
                )

        # Strict DB-backed combo consistency
        adapter_metadata = canonical_payload.get("adapter_metadata")
        if isinstance(adapter_metadata, dict):
            difficulty_consistency = adapter_metadata.get("difficulty_consistency")
            if isinstance(difficulty_consistency, dict):
                note_total_db = safe_int(difficulty_consistency.get("note_total_db"), default=None)
                note_delta_meta = safe_int(difficulty_consistency.get("note_delta"), default=None)

                diagnostics["note_total_db"] = note_total_db
                diagnostics["note_delta_meta"] = note_delta_meta

                if note_total_db is not None:
                    delta = compute_delta(combo_from_events, note_total_db)
                    diagnostics["db_combo_delta"] = delta

                    if delta is None:
                        errors.append(_err("P4_DB_DELTA_UNKNOWN", "could not compute DB combo delta"))
                    elif delta != MAX_DB_NOTE_DELTA:
                        errors.append(
                            _err(
                                "P4_DB_COMBO_MISMATCH",
                                f"DB-backed combo delta must be {MAX_DB_NOTE_DELTA}, got {delta} (payload_combo={combo_from_events}, note_total_db={note_total_db})",
                            )
                        )

                    if note_delta_meta is not None and note_delta_meta != MAX_DB_NOTE_DELTA:
                        errors.append(
                            _err(
                                "P4_DB_META_DELTA_MISMATCH",
                                f"adapter_metadata.difficulty_consistency.note_delta must be {MAX_DB_NOTE_DELTA}, got {note_delta_meta}",
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
            "supports_flicks": True,
            "supports_holds": True,
            "supports_db_combo_parity": True,
        }


__all__ = [
    "ProsekaValidator",
    "PROSEKA_RAW_TYPES",
    "COMBO_RAW_TYPES",
    "CANONICAL_KINDS",
    "MAX_DB_NOTE_DELTA",
]