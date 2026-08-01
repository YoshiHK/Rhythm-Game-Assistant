#!/usr/bin/env python3
from __future__ import annotations

from typing import Any, Dict, List, Optional

from ..base_validator_v2 import BaseValidatorV2
from ..common_validator_utils import safe_int, safe_float


_ALLOWED_DIFFICULTIES = {
    "EASY",
    "NORMAL",
    "HARD",
    "EXPERT",
    "SPECIAL",
}


class BandoriValidator(BaseValidatorV2):
    game_id = "bandori"
    validator_id = "validator_bandori"

    def validate_v2(
        self,
        payload: Dict[str, Any],
        *,
        canonical_payload: Optional[Dict[str, Any]] = None,
        canonical_row: Optional[Dict[str, Any]] = None,
        **context
    ) -> dict:

        errors: List[str] = []
        warnings: List[str] = []

        canonical_payload, canonical_row, _ = self.coerce_payload_and_row(
            payload,
            canonical_payload=canonical_payload,
            canonical_row=canonical_row,
        )

        resolved = self.resolve_identity_fields(
            canonical_payload,
            canonical_row,
        )

        # --------------------------------------------------
        # Identity (STRICT)
        # --------------------------------------------------
        if not resolved["game"]:
            errors.append("missing required field: game")

        if not resolved["chart_id"]:
            errors.append("missing required field: chart_id")

        if not resolved["difficulty"]:
            errors.append("missing required field: difficulty")

        if not resolved["title"]:
            warnings.append("missing title")

        if resolved["game"] != self.game_id:
            errors.append(f"game must be '{self.game_id}'")

        if resolved["difficulty"] and resolved["difficulty"] not in _ALLOWED_DIFFICULTIES:
            errors.append(
                f"invalid difficulty: {resolved['difficulty']} "
                f"(expected one of {sorted(_ALLOWED_DIFFICULTIES)})"
            )

        # --------------------------------------------------
        # Payload structure
        # --------------------------------------------------
        note_events = canonical_payload.get("note_events")
        if not isinstance(note_events, list):
            errors.append("note_events must be a list")
            note_events = []

        chart_meta = canonical_payload.get("chart_meta")
        if not isinstance(chart_meta, dict):
            errors.append("chart_meta must be a dict")
            chart_meta = {}

        # --------------------------------------------------
        # BPM sanity (minimal)
        # --------------------------------------------------
        bpm = safe_float(chart_meta.get("bpm"))
        if bpm is None or bpm <= 0:
            warnings.append("chart_meta.bpm is missing or non-positive")

        # --------------------------------------------------
        # Note events validation (lightweight)
        # --------------------------------------------------
        prev_t = -1.0

        for idx, ev in enumerate(note_events):
            if not isinstance(ev, dict):
                errors.append(f"note_events[{idx}] must be dict")
                continue

            tb = safe_float(ev.get("time_beats"))
            lane = safe_int(ev.get("lane"))

            if tb is None or tb < 0:
                errors.append(f"note_events[{idx}] invalid time_beats")
            else:
                if tb < prev_t:
                    errors.append("note_events not sorted")
                prev_t = tb

            if lane is None or lane <= 0:
                errors.append(f"note_events[{idx}] invalid lane")

        # --------------------------------------------------
        # Row parity (soft)
        # --------------------------------------------------
        ntc = canonical_row.get("note_total_chart") if isinstance(canonical_row, dict) else None
        ntc_int = safe_int(ntc, None)

        if ntc_int is not None:
            if abs(len(note_events) - ntc_int) > max(50, int(0.2 * max(1, ntc_int))):
                warnings.append("note_total_chart mismatch is large")

        # --------------------------------------------------
        # Final
        # --------------------------------------------------
        if errors:
            return self.fail_result(errors=errors, warnings=warnings)

        return self.ok_result(warnings=warnings)

    def capabilities(self) -> dict:
        return {
            "note_model": "lane_based",
            "supports_sections": True,
            "supports_variable_bpm": True,
            "beat_aligned": True,
        }


__all__ = ["BandoriValidator"]