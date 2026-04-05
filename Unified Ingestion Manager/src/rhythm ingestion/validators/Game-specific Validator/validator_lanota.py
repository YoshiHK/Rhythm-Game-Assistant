#!/usr/bin/env python3
"""validator_lanota.py

LanotaValidator (UMI Phase 3)

Validates:
- canonical_row minimal sanity
- canonical_payload.note_events structural integrity
- Lanota-specific geometry/timing invariants (radial charts)

Scope (Phase 3 only):
- Structural validation only
- No gameplay semantics
- No tips or Phase 4 logic

Designed to validate payloads emitted by adapter_lanota.py.
"""

from __future__ import annotations

from typing import Any, Dict, List

from .base_validator import BaseValidator


_ALLOWED_KINDS = {
    "tap",
    "hold_path",
}


class LanotaValidator(BaseValidator):
    game_id = "lanota"

    def validate(
        self,
        *,
        raw_chart: Any,
        canonical_payload: Dict[str, Any],
        canonical_row: Dict[str, Any],
    ) -> None:
        """Validate a single Lanota ingestion result.

        Raises ValueError on validation failures.
        """

        errors: List[str] = []

        # ----------------------------
        # Row-level sanity
        # ----------------------------
        required_row = ["game", "song_id", "note_total_chart"]
        for k in required_row:
            if k not in canonical_row:
                errors.append(f"Missing required field '{k}' in canonical_row.")

        if canonical_row.get("game") not in (self.game_id, "lanota"):
            errors.append(f"canonical_row['game'] must be 'lanota', got {canonical_row.get('game')!r}.")

        ntc = canonical_row.get("note_total_chart")
        if not isinstance(ntc, int) or ntc <= 0:
            errors.append(f"canonical_row['note_total_chart'] must be a positive int, got {ntc!r}.")

        self._fail_if(errors, stage="row", song_id=canonical_row.get("song_id"))

        # ----------------------------
        # Payload-level sanity
        # ----------------------------
        if canonical_payload.get("game_id") not in (None, self.game_id, "lanota"):
            errors.append(
                f"canonical_payload['game_id'] mismatch: expected 'lanota', got {canonical_payload.get('game_id')!r}."
            )

        note_events = canonical_payload.get("note_events")
        if not isinstance(note_events, list) or not note_events:
            errors.append("canonical_payload['note_events'] must be a non-empty list for lanota.")
            self._fail_if(errors, stage="payload", song_id=canonical_row.get("song_id"))
            return

        chart_meta = canonical_payload.get("chart_meta")
        if not isinstance(chart_meta, dict):
            errors.append("canonical_payload['chart_meta'] must be a dict.")
            self._fail_if(errors, stage="payload", song_id=canonical_row.get("song_id"))
            return

        bpm = chart_meta.get("bpm")
        if not isinstance(bpm, (int, float)) or float(bpm) <= 0:
            errors.append(f"chart_meta.bpm must be a positive number, got {bpm!r}.")

        max_time_beats = chart_meta.get("max_time_beats")
        if not isinstance(max_time_beats, (int, float)) or float(max_time_beats) < 0:
            errors.append(f"chart_meta.max_time_beats must be a non-negative number, got {max_time_beats!r}.")

        # ----------------------------
        # Note events integrity
        # ----------------------------
        prev_t: float = -1.0
        for idx, ev in enumerate(note_events):
            if not isinstance(ev, dict):
                errors.append(f"note_events[{idx}] must be an object, got {type(ev).__name__}.")
                continue

            tb = ev.get("time_beats")
            lane = ev.get("lane")
            kind = ev.get("kind")
            extra = ev.get("extra")

            # time
            if not isinstance(tb, (int, float)):
                errors.append(f"note_events[{idx}].time_beats must be number, got {type(tb).__name__}.")
            else:
                tbf = float(tb)
                if tbf < 0:
                    errors.append(f"note_events[{idx}].time_beats must be >= 0, got {tbf}.")
                if tbf < prev_t:
                    errors.append(
                        f"note_events[{idx}].time_beats={tbf} is less than previous time_beats={prev_t} (events must be sorted)."
                    )
                prev_t = tbf

            # lane (radial bucket)
            if not isinstance(lane, int):
                errors.append(f"note_events[{idx}].lane must be int, got {type(lane).__name__}.")
            elif lane <= 0:
                errors.append(f"note_events[{idx}].lane must be > 0, got {lane}.")

            # kind
            if not isinstance(kind, str):
                errors.append(f"note_events[{idx}].kind must be str, got {type(kind).__name__}.")
            elif kind not in _ALLOWED_KINDS:
                errors.append(f"note_events[{idx}].kind={kind!r} is not an allowed canonical kind for lanota.")

            # extra
            if extra is None or not isinstance(extra, dict):
                errors.append(f"note_events[{idx}].extra must be an object, got {type(extra).__name__}.")
                continue

            # Required preserved fields from adapter
            if "raw_type" not in extra:
                errors.append(f"note_events[{idx}].extra missing 'raw_type'.")
            if "degree" not in extra:
                errors.append(f"note_events[{idx}].extra missing 'degree'.")
            if "duration" not in extra:
                errors.append(f"note_events[{idx}].extra missing 'duration'.")

            # Hold consistency
            if kind == "hold_path":
                dur = extra.get("duration")
                try:
                    dur_f = float(dur)
                except Exception:
                    dur_f = -1.0
                if dur_f <= 0:
                    errors.append(
                        f"note_events[{idx}] kind='hold_path' but extra.duration={dur!r} is not > 0."
                    )

        # Row/payload parity (soft)
        if isinstance(ntc, int) and isinstance(note_events, list):
            if abs(len(note_events) - ntc) > max(50, int(0.2 * max(1, ntc))):
                errors.append(
                    f"Row/payload note_total_chart mismatch is too large: row={ntc}, payload_count={len(note_events)}."
                )

        self._fail_if(errors, stage="payload", song_id=canonical_row.get("song_id"))

    # ----------------------------
    # Helpers
    # ----------------------------
    @staticmethod
    def _fail_if(errors: List[str], *, stage: str, song_id: Any) -> None:
        if errors:
            raise ValueError(
                f"LanotaValidator ({stage}) failed for song_id={song_id!r}: " + "; ".join(errors)
            )

    def capabilities(self) -> dict:
        return {
            "note_model": "spatial",
            "supports_sections": False,
            "supports_variable_bpm": True,
            "radial_geometry": True,
        }


__all__ = ["LanotaValidator"]
