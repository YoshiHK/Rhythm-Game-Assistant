"""
ProsekaValidator

UMI Phase 3 game validator for Project SEKAI ("proseka").

Validates:
- canonical_row sanity (required keys, positivity)
- canonical_payload.note_events structural integrity
- combo parity between note_events, row fields, and adapter_metadata
- optional section consistency checks (only when section metadata exists)
- strict DB-backed combo consistency (MAX_DB_NOTE_DELTA = 0)

Also attaches diagnostics.metadata_parity for QA/debugging (non-blocking).

This module is Phase-3 wiring only and does not modify any Phase 1/2 logic.
It uses common_validator_utils for shared numeric/parity helpers.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from .base_validator import BaseValidator
from .common_validator_utils import (
    compute_delta,
    is_within_threshold,
    numeric_equal,
    values_equal,
)

# ---------------------------------------------------------------------
# Constants (must remain aligned with adapter output)
# ---------------------------------------------------------------------

# Allowed raw_type values for Proseka NoteEvents (extra["raw_type"])
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

# Subset of raw types that contribute to combo (judged hit events)
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

# Strict DB-backed consistency for Proseka: must match exactly.
MAX_DB_NOTE_DELTA = 0

# Canonical kinds allowed by canonical_chart_payload schema
CANONICAL_KINDS = {
    "tap",
    "critical_tap",
    "flick",
    "flick_arrow",
    "hold_body_or_start",
    "hold_path",
    "critical_hold_path",
}


class ProsekaValidator(BaseValidator):
    game_id = "proseka"

    def validate(
        self,
        *,
        raw_chart: Any,
        canonical_payload: Dict[str, Any],
        canonical_row: Dict[str, Any],
    ) -> None:
        """Validate a single Proseka ingestion result."""
        song_id = canonical_row.get("song_id")
        errors: List[str] = []

        # Phase 1: row-level checks
        self._validate_row_basic(canonical_row, errors)
        self._fail_if(errors, stage="row", song_id=song_id)

        # Phase 2: payload structure + core invariants
        self._validate_payload_structure(canonical_payload, canonical_row, errors)
        self._fail_if(errors, stage="structural", song_id=song_id)

        
        # inside ProsekaValidator.validate(), after payload structure check
        self._validate_pattern_tags(canonical_payload, errors, strict=False)


        # Phase 3: DB-backed consistency
        self._validate_db_consistency(canonical_payload, canonical_row, errors, song_id)

        # Always attach parity summary for QA (non-blocking)
        self._attach_metadata_parity_summary(canonical_payload, canonical_row, song_id)

        self._fail_if(errors, stage="consistency", song_id=song_id)

        
        from .common_validator_utils import (
            compute_phase4_gate_state,
            explain_gate_failures,
            build_validation_ok,
        )

        # after existing validation passes
        gate = compute_phase4_gate_state(
            engine_mode=canonical_payload.get("engine_mode"),
            feature_flags=canonical_payload.get("feature_flags"),
            opt_in=canonical_payload.get("opt_in"),
        )

        warnings = []
        degraded_mode = False

        if not gate["personalization_allowed"]:
            degraded_mode = True
            msg = explain_gate_failures(gate["gate_fail_reasons"])
            if msg:
                warnings.append(msg)

        return build_validation_ok(
            warnings=warnings,
            degraded_mode=degraded_mode,
        )

    
        def capabilities(self) -> dict:
            return {
                "note_model": "lane_based",
                "supports_sections": True,
                "supports_trace_notes": True,
                "supports_variable_bpm": True,
            }


    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _fail_if(errors: List[str], *, stage: str, song_id: Any) -> None:
        if errors:
            raise ValueError(
                f"ProsekaValidator ({stage}) failed for song_id={song_id!r}: "
                + "; ".join(errors)
            )

    def _validate_payload_structure(
        self,
        canonical_payload: Dict[str, Any],
        canonical_row: Dict[str, Any],
        errors: List[str],
    ) -> None:
        song_id = canonical_row.get("song_id")
        note_events = canonical_payload.get("note_events")
        sections = canonical_payload.get("sections")

        if not isinstance(note_events, list) or not note_events:
            errors.append(
                f"canonical_payload['note_events'] must be a non-empty list for song_id={song_id!r}."
            )
            return

        # Rule set 1: strict structural validation of note_events
        self._validate_note_events_structural(note_events, errors, song_id)
        if errors:
            return

        # Rule set 2: combo consistency & parity checks
        self._validate_combo_consistency(note_events, canonical_row, errors, song_id)
        self._validate_combo_symmetry(canonical_payload, canonical_row, errors, song_id)
        self._validate_bpm_symmetry(canonical_payload, canonical_row, errors, song_id)
        self._validate_duration_symmetry(canonical_payload, canonical_row, errors, song_id)

        # Rule set 3: optional section consistency
        if isinstance(sections, list) and sections and not errors:
            self._validate_sections_consistency(
                note_events, sections, canonical_row, errors, song_id
            )

    def _validate_row_basic(self, canonical_row: Dict[str, Any], errors: List[str]) -> None:
        required_keys = ["game", "song_id", "note_total_chart", "duration_ms"]
        for key in required_keys:
            if key not in canonical_row:
                errors.append(f"Missing required field '{key}' in canonical_row.")

        if errors:
            return

        game = canonical_row.get("game")
        song_id = canonical_row.get("song_id")
        note_total_chart = canonical_row.get("note_total_chart")
        duration_ms = canonical_row.get("duration_ms")

        if game != "proseka":
            errors.append(
                f"canonical_row['game'] must be 'proseka', got {game!r} for song_id={song_id!r}."
            )

        if not isinstance(note_total_chart, int):
            errors.append(
                f"canonical_row['note_total_chart'] must be int, got {type(note_total_chart).__name__}."
            )
        elif note_total_chart <= 0:
            errors.append(
                f"canonical_row['note_total_chart'] must be > 0, got {note_total_chart}."
            )

        if not isinstance(duration_ms, int):
            errors.append(
                f"canonical_row['duration_ms'] must be int, got {type(duration_ms).__name__}."
            )
        elif duration_ms <= 0:
            errors.append(f"canonical_row['duration_ms'] must be > 0, got {duration_ms}.")

        # note_total_chart vs note_total_db vs note_delta
        note_total_db = canonical_row.get("note_total_db")
        note_delta = canonical_row.get("note_delta")

        if isinstance(note_total_db, int) and isinstance(note_total_chart, int):
            expected_delta = compute_delta(note_total_chart, note_total_db)
            if expected_delta is None:
                expected_delta = abs(note_total_chart - note_total_db)

            if note_delta is None:
                canonical_row["note_delta"] = expected_delta
            elif not isinstance(note_delta, int):
                errors.append(
                    "canonical_row['note_delta'] must be int when note_total_db is set, "
                    f"got {type(note_delta).__name__}."
                )
            elif note_delta != expected_delta:
                errors.append(
                    "note_delta mismatch: expected "
                    f"{expected_delta} (|note_total_chart - note_total_db|), got {note_delta}."
                )

    def _validate_note_events_structural(
        self,
        note_events: List[Dict[str, Any]],
        errors: List[str],
        song_id: Any,
    ) -> None:
        hold_start_count = 0
        hold_end_count = 0
        prev_time: Optional[float] = None

        for idx, ev in enumerate(note_events):
            if not isinstance(ev, dict):
                errors.append(f"note_events[{idx}] must be an object, got {type(ev).__name__}.")
                continue

            if "time_beats" not in ev:
                errors.append(f"note_events[{idx}] missing 'time_beats'.")
                continue
            if "lane" not in ev:
                errors.append(f"note_events[{idx}] missing 'lane'.")
                continue
            if "kind" not in ev:
                errors.append(f"note_events[{idx}] missing 'kind'.")
                continue

            time_beats = ev["time_beats"]
            lane = ev["lane"]
            kind = ev["kind"]

            if not isinstance(time_beats, (int, float)):
                errors.append(
                    f"note_events[{idx}].time_beats must be number, got {type(time_beats).__name__}."
                )
            elif time_beats < 0:
                errors.append(f"note_events[{idx}].time_beats must be >= 0, got {time_beats}.")

            if not isinstance(lane, int):
                errors.append(f"note_events[{idx}].lane must be int, got {type(lane).__name__}.")

            if not isinstance(kind, str):
                errors.append(f"note_events[{idx}].kind must be str, got {type(kind).__name__}.")
            elif kind not in CANONICAL_KINDS:
                errors.append(f"note_events[{idx}].kind={kind!r} is not a valid canonical kind.")

            # Non-decreasing time order
            if isinstance(time_beats, (int, float)):
                tb = float(time_beats)
                if prev_time is not None and tb < prev_time:
                    errors.append(
                        f"note_events[{idx}].time_beats={tb} is less than previous time_beats={prev_time} "
                        "(events must be sorted)."
                    )
                prev_time = tb

            extra = ev.get("extra")
            if extra is None or not isinstance(extra, dict):
                errors.append(f"note_events[{idx}].extra must be an object, got {type(extra).__name__}.")
                continue

            raw_type = extra.get("raw_type")
            if not isinstance(raw_type, str):
                errors.append(
                    f"note_events[{idx}].extra['raw_type'] must be str, got {type(raw_type).__name__}."
                )
                continue

            if raw_type not in PROSEKA_RAW_TYPES:
                errors.append(
                    f"note_events[{idx}].extra['raw_type']={raw_type!r} is not a known Proseka raw_type."
                )

            if raw_type in ("hold_start", "hold_start_critical"):
                hold_start_count += 1
            if raw_type in ("hold_end", "hold_end_critical"):
                hold_end_count += 1

            if raw_type in (
                "trace_body_segment",
                "trace_tick",
                "trace_tick_critical",
                "trace_flick",
                "trace_flick_critical",
            ):
                shape = extra.get("shape")
                if shape != "trace":
                    errors.append(
                        f"note_events[{idx}] raw_type={raw_type!r} should have extra['shape']=='trace', got {shape!r}."
                    )

            if raw_type in ("flick", "flick_critical", "trace_flick", "trace_flick_critical"):
                direction = extra.get("direction")
                if not isinstance(direction, str) or not direction:
                    errors.append(
                        f"note_events[{idx}] raw_type={raw_type!r} should have non-empty extra['direction']."
                    )

            if raw_type in ("hold_body_segment", "trace_body_segment"):
                rect_height = extra.get("rect_height")
                if rect_height is not None:
                    if not isinstance(rect_height, (int, float)):
                        errors.append(
                            f"note_events[{idx}].extra['rect_height'] must be number when present, got {type(rect_height).__name__}."
                        )
                    elif rect_height <= 0:
                        errors.append(
                            f"note_events[{idx}].extra['rect_height'] should be > 0 for raw_type={raw_type!r}, got {rect_height}."
                        )

        if hold_start_count != hold_end_count:
            errors.append(
                f"Hold start/end mismatch in note_events for song_id={song_id!r}: "
                f"hold_start_count={hold_start_count}, hold_end_count={hold_end_count}."
            )

    @staticmethod
    def _count_combo_from_events(note_events: List[Dict[str, Any]]) -> int:
        c = 0
        for ev in note_events:
            if not isinstance(ev, dict):
                continue
            extra = ev.get("extra")
            if not isinstance(extra, dict):
                continue
            rt = extra.get("raw_type")
            if rt in COMBO_RAW_TYPES:
                c += 1
        return c

    def _validate_combo_consistency(
        self,
        note_events: List[Dict[str, Any]],
        canonical_row: Dict[str, Any],
        errors: List[str],
        song_id: Any,
    ) -> None:
        combo_from_events = self._count_combo_from_events(note_events)
        note_total_chart = canonical_row.get("note_total_chart")

        if not isinstance(note_total_chart, int):
            errors.append(
                f"canonical_row['note_total_chart'] must be int for combo checks (song_id={song_id!r})."
            )
            return

        if combo_from_events != note_total_chart:
            errors.append(
                f"Combo mismatch: combo_from_events={combo_from_events} != canonical_row['note_total_chart']={note_total_chart} "
                f"for song_id={song_id!r}."
            )

    def _validate_combo_symmetry(
        self,
        canonical_payload: Dict[str, Any],
        canonical_row: Dict[str, Any],
        errors: List[str],
        song_id: Any,
    ) -> None:
        adapter_meta = canonical_payload.get("adapter_metadata") or {}
        diff_consistency = adapter_meta.get("difficulty_consistency") or {}

        combo_meta = diff_consistency.get("combo_from_events")
        combo_row = canonical_row.get("note_total_chart")

        eq = values_equal(combo_meta, combo_row)
        if eq is False:
            errors.append(
                f"Combo symmetry mismatch: adapter_metadata.difficulty_consistency.combo_from_events={combo_meta} "
                f"!= canonical_row['note_total_chart']={combo_row} for song_id={song_id!r}."
            )

    def _validate_bpm_symmetry(
        self,
        canonical_payload: Dict[str, Any],
        canonical_row: Dict[str, Any],
        errors: List[str],
        song_id: Any,
    ) -> None:
        chart_meta = canonical_payload.get("chart_meta") or {}
        adapter_meta = canonical_payload.get("adapter_metadata") or {}
        diff_details = adapter_meta.get("difficulty_details") or {}

        bpm_chart = chart_meta.get("bpm")
        bpm_row = canonical_row.get("bpm")
        bpm_db = diff_details.get("bpm_db")

        if bpm_row is not None and bpm_chart is not None and numeric_equal(bpm_row, bpm_chart, tol=0.0) is False:
            errors.append(
                f"BPM mismatch: canonical_row['bpm']={bpm_row} != chart_meta['bpm']={bpm_chart} for song_id={song_id!r}."
            )

        if bpm_db is not None and bpm_chart is not None and numeric_equal(bpm_db, bpm_chart, tol=0.0) is False:
            errors.append(
                f"BPM mismatch: difficulty_details['bpm_db']={bpm_db} != chart_meta['bpm']={bpm_chart} for song_id={song_id!r}."
            )

    def _validate_duration_symmetry(
        self,
        canonical_payload: Dict[str, Any],
        canonical_row: Dict[str, Any],
        errors: List[str],
        song_id: Any,
    ) -> None:
        # Informational-only (duration parity is attached via diagnostics metadata_parity).
        _ = (canonical_payload, canonical_row, errors, song_id)
        return

    def _validate_sections_consistency(
        self,
        note_events: List[Dict[str, Any]],
        sections: List[Dict[str, Any]],
        canonical_row: Dict[str, Any],
        errors: List[str],
        song_id: Any,
    ) -> None:
        note_total_chart = canonical_row.get("note_total_chart")
        if not isinstance(note_total_chart, int):
            return

        have_expected_combo = True
        sum_expected = 0
        for idx, sec in enumerate(sections):
            if not isinstance(sec, dict):
                errors.append(f"sections[{idx}] must be an object, got {type(sec).__name__}.")
                have_expected_combo = False
                continue
            etc = sec.get("expected_total_combo")
            if etc is None:
                have_expected_combo = False
                continue
            if not isinstance(etc, int):
                errors.append(
                    f"sections[{idx}]['expected_total_combo'] must be int when present, got {type(etc).__name__}."
                )
                have_expected_combo = False
                continue
            if etc < 0:
                errors.append(f"sections[{idx}]['expected_total_combo'] should be >= 0, got {etc}.")
                have_expected_combo = False
                continue
            sum_expected += etc

        if have_expected_combo and sum_expected != note_total_chart:
            errors.append(
                "Section combo mismatch: sum(sections[*].expected_total_combo) "
                f"= {sum_expected}, but canonical_row['note_total_chart'] "
                f"= {note_total_chart} for song_id={song_id!r}."
            )

        have_boundaries = True
        intervals: List[tuple] = []
        prev_end: Optional[float] = None

        for idx, sec in enumerate(sections):
            if not isinstance(sec, dict):
                continue
            sb = sec.get("start_beats")
            eb = sec.get("end_beats")
            if sb is None or eb is None:
                have_boundaries = False
                continue
            if not isinstance(sb, (int, float)) or not isinstance(eb, (int, float)):
                errors.append(f"sections[{idx}]['start_beats'/'end_beats'] must be numbers when present.")
                have_boundaries = False
                continue
            sb_f = float(sb)
            eb_f = float(eb)
            if sb_f >= eb_f:
                errors.append(
                    f"sections[{idx}] has invalid beats interval: start_beats={sb_f} >= end_beats={eb_f}."
                )
            if prev_end is not None and sb_f < prev_end:
                errors.append(
                    f"sections[{idx}] starts at {sb_f} beats, which is before previous section end_beats={prev_end}."
                )
            prev_end = eb_f
            intervals.append((sb_f, eb_f))

        if have_boundaries and intervals and not errors:
            for idx, ev in enumerate(note_events):
                extra = ev.get("extra")
                if not isinstance(extra, dict):
                    continue
                raw_type = extra.get("raw_type")
                if raw_type not in COMBO_RAW_TYPES:
                    continue
                tb = ev.get("time_beats")
                if not isinstance(tb, (int, float)):
                    continue
                tb_f = float(tb)
                covered = any(sb <= tb_f < eb for sb, eb in intervals)
                if not covered:
                    errors.append(
                        f"Combo-contributing event note_events[{idx}] at time_beats={tb_f} is not inside any section "
                        f"[start_beats, end_beats) for song_id={song_id!r}."
                    )
                    break

    def _validate_db_consistency(
        self,
        canonical_payload: Dict[str, Any],
        canonical_row: Dict[str, Any],
        errors: List[str],
        song_id: Any,
    ) -> None:
        note_total_chart = canonical_row.get("note_total_chart")
        note_total_db = canonical_row.get("note_total_db")
        note_delta = canonical_row.get("note_delta")

        adapter_meta = canonical_payload.get("adapter_metadata") or {}
        diff_consistency = adapter_meta.get("difficulty_consistency") or {}

        meta_note_total_db = diff_consistency.get("note_total_db")
        meta_note_delta = diff_consistency.get("note_delta")
        meta_threshold = diff_consistency.get("note_delta_threshold")
        meta_is_consistent = diff_consistency.get("is_consistent")

        threshold = MAX_DB_NOTE_DELTA
        if isinstance(meta_threshold, int) and meta_threshold >= 0:
            threshold = meta_threshold

        # Fill missing row note_total_db from metadata if available
        if note_total_db is None and isinstance(meta_note_total_db, int):
            note_total_db = meta_note_total_db
            canonical_row["note_total_db"] = note_total_db

        if note_total_db is None:
            errors.append(
                "DB-backed consistency is enabled, but canonical_row['note_total_db'] is None "
                f"for song_id={song_id!r} (adapter_metadata.difficulty_consistency={diff_consistency})."
            )
            return

        if not isinstance(note_total_db, int):
            errors.append(
                "canonical_row['note_total_db'] must be int for DB-backed validation, "
                f"got {type(note_total_db).__name__} (adapter_metadata.difficulty_consistency={diff_consistency})."
            )
            return

        if not isinstance(note_total_chart, int):
            return

        # Choose diff: row note_delta else metadata note_delta else compute
        if isinstance(note_delta, int):
            diff = note_delta
        elif isinstance(meta_note_delta, int):
            diff = meta_note_delta
            canonical_row["note_delta"] = diff
        else:
            d = compute_delta(note_total_chart, note_total_db)
            diff = int(d) if d is not None else abs(note_total_chart - note_total_db)
            canonical_row["note_delta"] = diff

        within = is_within_threshold(diff, threshold)
        if within is False or (meta_is_consistent is False):
            errors.append(
                "DB-backed combo mismatch: official note_total_db="
                f"{note_total_db}, parsed note_total_chart={note_total_chart}, "
                f"difference={diff} exceeds allowed threshold={threshold} "
                f"for song_id={song_id!r}. adapter_metadata.difficulty_consistency={diff_consistency}."
            )

    def _attach_metadata_parity_summary(
        self,
        canonical_payload: Dict[str, Any],
        canonical_row: Dict[str, Any],
        song_id: Any,
    ) -> None:
        diagnostics = canonical_payload.get("diagnostics")
        if not isinstance(diagnostics, dict):
            diagnostics = {}
            canonical_payload["diagnostics"] = diagnostics

        chart_meta = canonical_payload.get("chart_meta") or {}
        adapter_meta = canonical_payload.get("adapter_metadata") or {}
        diff_details = adapter_meta.get("difficulty_details") or {}
        diff_consistency = adapter_meta.get("difficulty_consistency") or {}

        # Combo recomputed from events
        note_events = canonical_payload.get("note_events") or []
        combo_from_events_actual = 0
        if isinstance(note_events, list):
            for ev in note_events:
                if not isinstance(ev, dict):
                    continue
                extra = ev.get("extra")
                if not isinstance(extra, dict):
                    continue
                rt = extra.get("raw_type")
                if rt in COMBO_RAW_TYPES:
                    combo_from_events_actual += 1

        combo_row = canonical_row.get("note_total_chart")
        combo_db_row = canonical_row.get("note_total_db")
        combo_meta = diff_consistency.get("combo_from_events")
        combo_db_meta = diff_consistency.get("note_total_db")

        bpm_chart = chart_meta.get("bpm")
        bpm_row = canonical_row.get("bpm")
        bpm_db = diff_details.get("bpm_db")

        max_time_beats = chart_meta.get("max_time_beats")
        duration_from_chart_ms = None
        if (
            isinstance(max_time_beats, (int, float))
            and isinstance(bpm_chart, (int, float))
            and float(bpm_chart) > 0
        ):
            duration_from_chart_ms = int(float(max_time_beats) * 60000.0 / float(bpm_chart))

        duration_row_ms = canonical_row.get("duration_ms")
        duration_db_ms = diff_details.get("duration_ms_db")

        metadata_parity = {
            "song_id": song_id,
            "combo": {
                "combo_from_events_actual": combo_from_events_actual,
                "combo_row": combo_row,
                "combo_db_row": combo_db_row,
                "combo_from_metadata": combo_meta,
                "combo_db_meta": combo_db_meta,
                "row_equals_events": values_equal(combo_row, combo_from_events_actual) is True,
                "row_equals_db_row": values_equal(combo_row, combo_db_row) is True,
                "events_equals_db_meta": values_equal(combo_db_meta, combo_from_events_actual) is True,
            },
            "bpm": {
                "bpm_chart": bpm_chart,
                "bpm_row": bpm_row,
                "bpm_db": bpm_db,
                "row_equals_chart": numeric_equal(bpm_chart, bpm_row, tol=0.0) is True,
                "chart_equals_db": numeric_equal(bpm_chart, bpm_db, tol=0.0) is True,
                "row_equals_db": numeric_equal(bpm_row, bpm_db, tol=0.0) is True,
            },
            "duration_ms": {
                "from_chart": duration_from_chart_ms,
                "row": duration_row_ms,
                "db": duration_db_ms,
                "row_minus_chart": None
                if not (isinstance(duration_from_chart_ms, int) and isinstance(duration_row_ms, int))
                else duration_row_ms - duration_from_chart_ms,
                "db_minus_chart": None
                if not (isinstance(duration_from_chart_ms, int) and isinstance(duration_db_ms, int))
                else duration_db_ms - duration_from_chart_ms,
                "row_minus_db": None
                if not (isinstance(duration_row_ms, int) and isinstance(duration_db_ms, int))
                else duration_row_ms - duration_db_ms,
            },
        }

        diagnostics["metadata_parity"] = metadata_parity


__all__ = [
    "ProsekaValidator",
    "PROSEKA_RAW_TYPES",
    "COMBO_RAW_TYPES",
    "CANONICAL_KINDS",
    "MAX_DB_NOTE_DELTA",
]
