#!/usr/bin/env python3
"""validator_chunithm.py

ChunithmValidator (UMI Phase 3)

Validates:
- canonical_row minimal sanity
- canonical_payload.note_events structural integrity
- CHUNITHM-specific structural invariants derived from adapter_chunithm.py

Scope (Phase 3 only):
- Structural validation only
- No gameplay advice, no tips, no Phase 4 logic

Designed to validate payloads emitted by adapter_chunithm.py.

Note on BPM:
- adapter_chunithm.py sets chart_meta.bpm from BPM_DEF[0] when available, else 0.0.
- This validator allows bpm==0 only if bpm_changes exists with at least one positive BPM.
"""

from __future__ import annotations

from typing import Any, Dict, List

from .base_validator import BaseValidator


_ALLOWED_KINDS = {
    "tap",
    "critical_tap",
    "flick_arrow",
    "hold_path",
}


class ChunithmValidator(BaseValidator):
    game_id = "chunithm"

    def validate(
        self,
        *,
        raw_chart: Any,
        canonical_payload: Dict[str, Any],
        canonical_row: Dict[str, Any],
    ) -> None:
        errors: List[str] = []

        # ----------------------------
        # Row-level sanity
        # ----------------------------
        required_row = ["game", "song_id", "note_total_chart"]
        for k in required_row:
            if k not in canonical_row:
                errors.append(f"Missing required field '{k}' in canonical_row.")

        if canonical_row.get("game") not in (self.game_id, "chunithm"):
            errors.append(f"canonical_row['game'] must be 'chunithm', got {canonical_row.get('game')!r}.")

        ntc = canonical_row.get("note_total_chart")
        if not isinstance(ntc, int) or ntc <= 0:
            errors.append(f"canonical_row['note_total_chart'] must be a positive int, got {ntc!r}.")

        self._fail_if(errors, stage="row", song_id=canonical_row.get("song_id"))

        # ----------------------------
        # Payload-level sanity
        # ----------------------------
        if canonical_payload.get("game_id") not in (None, self.game_id, "chunithm"):
            errors.append(
                f"canonical_payload['game_id'] mismatch: expected 'chunithm', got {canonical_payload.get('game_id')!r}."
            )

        note_events = canonical_payload.get("note_events")
        if not isinstance(note_events, list) or not note_events:
            errors.append("canonical_payload['note_events'] must be a non-empty list for chunithm.")
            self._fail_if(errors, stage="payload", song_id=canonical_row.get("song_id"))
            return

        chart_meta = canonical_payload.get("chart_meta")
        if not isinstance(chart_meta, dict):
            errors.append("canonical_payload['chart_meta'] must be a dict.")
            self._fail_if(errors, stage="payload", song_id=canonical_row.get("song_id"))
            return

        bpm = chart_meta.get("bpm")
        bpm_changes = chart_meta.get("bpm_changes")
        if not isinstance(bpm, (int, float)):
            errors.append(f"chart_meta.bpm must be a number, got {bpm!r}.")
        else:
            bpm_f = float(bpm)
            if bpm_f <= 0:
                # Allow bpm==0 only if bpm_changes has at least one positive bpm
                ok_from_changes = False
                if isinstance(bpm_changes, list) and bpm_changes:
                    for bc in bpm_changes:
                        if isinstance(bc, dict) and isinstance(bc.get("bpm"), (int, float)) and float(bc.get("bpm")) > 0:
                            ok_from_changes = True
                            break
                if not ok_from_changes:
                    errors.append(f"chart_meta.bpm must be positive unless bpm_changes provides a positive BPM; got {bpm_f}.")

        max_time_beats = chart_meta.get("max_time_beats")
        if not isinstance(max_time_beats, (int, float)) or float(max_time_beats) < 0:
            errors.append(f"chart_meta.max_time_beats must be a non-negative number, got {max_time_beats!r}.")

        resolution = chart_meta.get("resolution")
        if resolution is not None:
            if not isinstance(resolution, int) or resolution <= 0:
                errors.append(f"chart_meta.resolution must be a positive int when present, got {resolution!r}.")

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

            # lane
            if not isinstance(lane, int):
                errors.append(f"note_events[{idx}].lane must be int, got {type(lane).__name__}.")
            else:
                if lane <= 0:
                    errors.append(f"note_events[{idx}].lane must be > 0, got {lane}.")
                # CHUNITHM has 16 columns -> lane should generally be 1..16, but keep non-strict

            # kind
            if not isinstance(kind, str):
                errors.append(f"note_events[{idx}].kind must be str, got {type(kind).__name__}.")
            elif kind not in _ALLOWED_KINDS:
                errors.append(f"note_events[{idx}].kind={kind!r} is not an allowed canonical kind for chunithm.")

            # extra
            if extra is None or not isinstance(extra, dict):
                errors.append(f"note_events[{idx}].extra must be an object, got {type(extra).__name__}.")
                continue

            # Required fields from adapter
            for req in ("raw_type", "measure", "offset", "cell", "width_lanes", "resolution"):
                if req not in extra:
                    errors.append(f"note_events[{idx}].extra missing {req!r}.")

            raw_type = extra.get("raw_type")
            if kind == "critical_tap" and raw_type != "CHR":
                errors.append(f"note_events[{idx}] kind='critical_tap' but extra.raw_type={raw_type!r} (expected 'CHR').")
            if kind == "flick_arrow" and raw_type != "FLK":
                errors.append(f"note_events[{idx}] kind='flick_arrow' but extra.raw_type={raw_type!r} (expected 'FLK').")

            # Hold consistency
            if kind == "hold_path":
                dur_raw = extra.get("duration_raw")
                dur_beats = extra.get("duration_beats")
                dur_ok = False
                try:
                    if dur_raw is not None and float(dur_raw) > 0:
                        dur_ok = True
                except Exception:
                    pass
                try:
                    if dur_beats is not None and float(dur_beats) > 0:
                        dur_ok = True
                except Exception:
                    pass
                if not dur_ok:
                    errors.append(
                        f"note_events[{idx}] kind='hold_path' but duration_raw/duration_beats is missing or non-positive."
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
                f"ChunithmValidator ({stage}) failed for song_id={song_id!r}: " + "; ".join(errors)
            )

    def capabilities(self) -> dict:
        return {
            "note_model": "lane_based",
            "supports_sections": False,
            "supports_variable_bpm": True,
            "supports_bpm_changes": True,
            "supports_width": True,
            "supports_air_notes": True,
        }


__all__ = ["ChunithmValidator"]
