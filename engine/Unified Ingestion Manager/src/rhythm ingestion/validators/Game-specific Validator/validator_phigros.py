#!/usr/bin/env python3
"""validator_phigros.py

PhigrosValidator (UMI Phase 3)

Validates:
- canonical_row minimal sanity
- canonical_payload.note_events structural integrity
- basic geometry/timing invariants for Phigros judge-line charts

This validator is Phase-3 wiring only:
- No gameplay difficulty inference
- No tips logic
- No Phase 4 execution

It is designed to validate payloads emitted by adapter_phigros.py.
"""

from __future__ import annotations

from typing import Any, Dict, List

from .base_validator import BaseValidator


# Canonical kinds allowed by canonical_chart_payload schema (subset used by adapter_phigros)
_ALLOWED_KINDS = {
    "tap",
    "hold_path",
}


class PhigrosValidator(BaseValidator):
    game_id = "phigros"

    def validate(
        self,
        *,
        raw_chart: Any,
        canonical_payload: Dict[str, Any],
        canonical_row: Dict[str, Any],
    ) -> None:
        """Validate a single Phigros ingestion result.

        Raises ValueError on validation failures (consistent with other Phase-3 validators).
        """

        errors: List[str] = []

        # ----------------------------
        # Row-level minimal sanity
        # ----------------------------
        required_row = ["game", "song_id", "note_total_chart"]
        for k in required_row:
            if k not in canonical_row:
                errors.append(f"Missing required field '{k}' in canonical_row.")
        if canonical_row.get("game") not in ("phigros", self.game_id):
            errors.append(f"canonical_row['game'] must be 'phigros', got {canonical_row.get('game')!r}.")
        ntc = canonical_row.get("note_total_chart")
        if not isinstance(ntc, int) or ntc <= 0:
            errors.append(f"canonical_row['note_total_chart'] must be a positive int, got {ntc!r}.")

        self._fail_if(errors, stage="row", song_id=canonical_row.get("song_id"))

        # ----------------------------
        # Payload structural sanity
        # ----------------------------
        if canonical_payload.get("game_id") not in (None, "phigros", self.game_id):
            errors.append(
                f"canonical_payload['game_id'] mismatch: expected 'phigros', got {canonical_payload.get('game_id')!r}."
            )

        note_events = canonical_payload.get("note_events")
        if not isinstance(note_events, list) or not note_events:
            errors.append("canonical_payload['note_events'] must be a non-empty list for phigros.")
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

            if not isinstance(lane, int):
                errors.append(f"note_events[{idx}].lane must be int, got {type(lane).__name__}.")
            elif lane <= 0:
                errors.append(f"note_events[{idx}].lane must be > 0, got {lane}.")

            if not isinstance(kind, str):
                errors.append(f"note_events[{idx}].kind must be str, got {type(kind).__name__}.")
            elif kind not in _ALLOWED_KINDS:
                errors.append(f"note_events[{idx}].kind={kind!r} is not an allowed canonical kind for this adapter.")

            if extra is None or not isinstance(extra, dict):
                errors.append(f"note_events[{idx}].extra must be an object, got {type(extra).__name__}.")
                continue

            # Phigros adapter preserves original fields in extra
            if "raw_type" not in extra:
                errors.append(f"note_events[{idx}].extra missing 'raw_type'.")
            if "positionX" not in extra:
                errors.append(f"note_events[{idx}].extra missing 'positionX'.")
            if "holdTime" not in extra:
                errors.append(f"note_events[{idx}].extra missing 'holdTime'.")
            if "judge_line_index" not in extra:
                errors.append(f"note_events[{idx}].extra missing 'judge_line_index'.")

            # Basic hold consistency: hold_path should have holdTime > 0
            ht = extra.get("holdTime")
            if kind == "hold_path":
                try:
                    ht_f = float(ht)
                except Exception:
                    ht_f = -1.0
                if ht_f <= 0.0:
                    errors.append(
                        f"note_events[{idx}] kind='hold_path' but extra.holdTime={ht!r} is not > 0."
                    )

        # Note count parity (soft): row note_total_chart should be close to payload count.
        # We keep this non-strict because different phigros note types may be counted differently.
        if isinstance(ntc, int) and isinstance(note_events, list):
            if abs(len(note_events) - ntc) > max(50, int(0.2 * max(1, ntc))):
                # record as error for now because row is produced from payload in our adapter;
                # large divergence suggests corrupted payload/row.
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
                f"PhigrosValidator ({stage}) failed for song_id={song_id!r}: " + "; ".join(errors)
            )

    def capabilities(self) -> dict:
        return {
            "note_model": "spatial",
            "supports_sections": False,
            "supports_variable_bpm": True,
            "judge_line_based": True,
        }


__all__ = ["PhigrosValidator"]
