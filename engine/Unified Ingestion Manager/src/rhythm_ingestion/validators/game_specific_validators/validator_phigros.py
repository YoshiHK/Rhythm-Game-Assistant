#!/usr/bin/env python3
from __future__ import annotations

"""
validator_phigros.py (FULL REPLACEMENT - v2 normalized)

Phase 3 validator for Phigros.

Scope:
- canonical_payload validation
- geometry-consistent note structure checks
- identity validation
- adapter-aligned contract enforcement

No gameplay logic / no tips inference.
"""

from typing import Any, Dict, List, Optional

from ..base_validator_v2 import BaseValidatorV2
from ..common_validator_utils import (
    safe_int,
    safe_float,
    values_equal,
    build_validation_ok,
    build_validation_fail,
)

# ---------------------------------------------------------------------
GAME_ID = "phigros"

CANONICAL_KINDS = {
    "tap",
    "hold_path",
}


def _err(code: str, msg: str) -> str:
    return f"{code}: {msg}"


def _warn(code: str, msg: str) -> str:
    return f"{code}: {msg}"


# ---------------------------------------------------------------------
class PhigrosValidator(BaseValidatorV2):
    game_id = GAME_ID
    validator_id = "validator_phigros"

    def validate_v2(
        self,
        payload: Dict[str, Any],
        *,
        canonical_payload: Optional[Dict[str, Any]] = None,
        canonical_row: Optional[Dict[str, Any]] = None,
        **_: Any,
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

        identity = self.resolve_identity_fields(
            canonical_payload,
            canonical_row,
        )

        # --------------------------------------------------
        # Identity validation
        # --------------------------------------------------
        if not identity["game"]:
            errors.append(_err("P0_GAME", "missing game"))

        if identity["game"] and identity["game"] != self.game_id:
            errors.append(_err("P0_GAME_MISMATCH", f"{identity['game']} != {self.game_id}"))

        if not identity["chart_id"]:
            errors.append(_err("P0_CHART_ID", "missing chart_id"))

        if not identity["title"]:
            warnings.append(_warn("P0_TITLE", "missing title"))

        if not identity["difficulty"]:
            warnings.append(_warn("P0_DIFF", "missing difficulty"))

        # --------------------------------------------------
        # chart_meta validation
        # --------------------------------------------------
        chart_meta = canonical_payload.get("chart_meta")
        if not isinstance(chart_meta, dict):
            errors.append(_err("P1_META", "chart_meta must be dict"))
            chart_meta = {}

        bpm = safe_float(chart_meta.get("bpm"))
        if bpm is not None and bpm <= 0:
            warnings.append(_warn("P1_BPM", "non-positive bpm"))

        max_tb = safe_float(chart_meta.get("max_time_beats"))
        if max_tb is None or max_tb < 0:
            errors.append(_err("P1_TIME", "invalid max_time_beats"))

        # --------------------------------------------------
        # note_events validation
        # --------------------------------------------------
        events = canonical_payload.get("note_events")
        if not isinstance(events, list):
            errors.append(_err("P2_EVENTS", "note_events must be list"))
            events = []

        if not events:
            errors.append(_err("P2_EMPTY", "note_events empty"))

        prev_tb: Optional[float] = None

        for i, ev in enumerate(events):
            if not isinstance(ev, dict):
                errors.append(_err("P2_TYPE", f"event[{i}] not dict"))
                continue

            tb = safe_float(ev.get("time_beats"))
            lane = ev.get("lane")
            kind = ev.get("kind")
            extra = ev.get("extra")

            # time
            if tb is None:
                errors.append(_err("P2_TIME", f"event[{i}] missing time"))
            else:
                if tb < 0:
                    errors.append(_err("P2_TIME_NEG", "time < 0"))
                if prev_tb is not None and tb < prev_tb:
                    errors.append(_err("P2_ORDER", "time not monotonic"))
                prev_tb = tb

            # lane (geometry fallback-friendly)
            if not isinstance(lane, int):
                errors.append(_err("P2_LANE", f"invalid lane type"))
            elif lane < 0:
                errors.append(_err("P2_LANE_NEG", "lane < 0"))

            # kind
            if not isinstance(kind, str):
                errors.append(_err("P2_KIND", "invalid kind"))
            elif kind not in CANONICAL_KINDS:
                errors.append(_err("P2_KIND_UNKNOWN", f"{kind} invalid"))

            # extra
            if not isinstance(extra, dict):
                errors.append(_err("P2_EXTRA", "extra must be dict"))
                continue

            # soft geometry checks
            if "positionX" not in extra:
                warnings.append(_warn("P3_GEOM_X", "missing positionX"))

            if "judge_line_index" not in extra:
                warnings.append(_warn("P3_LINE", "missing judge_line_index"))

            # hold consistency
            if kind == "hold_path":
                ht = safe_float(extra.get("holdTime"), default=0.0)
                if ht is None or ht <= 0:
                    errors.append(_err("P3_HOLD", "invalid holdTime"))

        # --------------------------------------------------
        # row parity
        # --------------------------------------------------
        if isinstance(canonical_row, dict):
            row_count = canonical_row.get("note_total_chart")
            if isinstance(row_count, int):
                if abs(len(events) - row_count) > max(50, int(len(events) * 0.2)):
                    warnings.append(_warn("P4_ROW", "row mismatch"))

        # --------------------------------------------------
        # degraded mode
        # --------------------------------------------------
        degraded_mode = True
        warnings.append("Phigros tips not enabled (Phase 3 only)")

        diagnostics["note_event_count"] = len(events)

        if errors:
            return build_validation_fail(
                errors=errors,
                warnings=warnings,
                degraded_mode=degraded_mode,
            )

        return build_validation_ok(
            warnings=warnings,
            degraded_mode=degraded_mode,
        )

    def validate_row(self, canonical_row: Dict[str, Any]) -> dict:
        return self.validate(canonical_row=canonical_row)

    def capabilities(self) -> dict:
        return {
            "note_model": "spatial",
            "supports_sections": False,
            "supports_variable_bpm": True,
            "judge_line_based": True,
            "canonical_kinds": list(CANONICAL_KINDS),
            "tips_supported": False,
        }


__all__ = ["PhigrosValidator"]