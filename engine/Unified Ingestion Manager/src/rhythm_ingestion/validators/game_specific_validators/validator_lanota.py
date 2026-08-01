#!/usr/bin/env python3
from __future__ import annotations

"""
validator_lanota.py (FULL REPLACEMENT - v2 normalized)

Phase 3 validator for Lanota.

Scope:
- canonical payload validation
- radial geometry consistency
- timing / ordering checks
- identity validation

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
GAME_ID = "lanota"

CANONICAL_KINDS = {
    "tap",
    "hold_path",
}


def _err(code: str, msg: str) -> str:
    return f"{code}: {msg}"


def _warn(code: str, msg: str) -> str:
    return f"{code}: {msg}"


# ---------------------------------------------------------------------
class LanotaValidator(BaseValidatorV2):
    game_id = GAME_ID
    validator_id = "validator_lanota"

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
            errors.append(_err("L0_GAME", "missing game"))

        if identity["game"] and identity["game"] != self.game_id:
            errors.append(_err("L0_GAME_MISMATCH", "incorrect game"))

        if not identity["chart_id"]:
            errors.append(_err("L0_CHART_ID", "missing chart_id"))

        if not identity["title"]:
            warnings.append(_warn("L0_TITLE", "missing title"))

        if not identity["difficulty"]:
            warnings.append(_warn("L0_DIFF", "missing difficulty"))

        # --------------------------------------------------
        # chart_meta validation
        # --------------------------------------------------
        chart_meta = canonical_payload.get("chart_meta")
        if not isinstance(chart_meta, dict):
            errors.append(_err("L1_META", "chart_meta must be dict"))
            chart_meta = {}

        bpm = safe_float(chart_meta.get("bpm"))
        if bpm is None or bpm <= 0:
            warnings.append(_warn("L1_BPM", "non-positive bpm"))

        max_tb = safe_float(chart_meta.get("max_time_beats"))
        if max_tb is None or max_tb < 0:
            errors.append(_err("L1_TIME", "invalid max_time_beats"))

        # --------------------------------------------------
        # note_events validation
        # --------------------------------------------------
        events = canonical_payload.get("note_events")
        if not isinstance(events, list):
            errors.append(_err("L2_EVENTS", "note_events must be list"))
            events = []

        if not events:
            errors.append(_err("L2_EMPTY", "note_events empty"))

        prev_tb: Optional[float] = None

        for i, ev in enumerate(events):
            if not isinstance(ev, dict):
                errors.append(_err("L2_TYPE", f"event[{i}] not dict"))
                continue

            tb = safe_float(ev.get("time_beats"))
            lane = ev.get("lane")
            kind = ev.get("kind")
            extra = ev.get("extra")

            # time ordering
            if tb is None:
                errors.append(_err("L2_TIME", "missing time"))
            else:
                if tb < 0:
                    errors.append(_err("L2_TIME_NEG", "negative time"))
                if prev_tb is not None and tb < prev_tb:
                    errors.append(_err("L2_ORDER", "time not monotonic"))
                prev_tb = tb

            # lane (radial bucket)
            if not isinstance(lane, int):
                errors.append(_err("L2_LANE", "invalid lane type"))
            elif lane < 0:
                errors.append(_err("L2_LANE_NEG", "lane < 0"))

            # kind
            if not isinstance(kind, str):
                errors.append(_err("L2_KIND", "invalid kind"))
            elif kind not in CANONICAL_KINDS:
                errors.append(_err("L2_KIND_UNKNOWN", f"{kind} not allowed"))

            # extra
            if not isinstance(extra, dict):
                errors.append(_err("L2_EXTRA", "extra must be dict"))
                continue

            # soft checks (non-fatal)
            if "degree" not in extra:
                warnings.append(_warn("L3_GEOM", "missing degree"))

            if kind == "hold_path":
                dur = safe_float(extra.get("duration"), default=0.0)
                if dur is None or dur <= 0:
                    errors.append(_err("L3_HOLD", "invalid hold duration"))

        # --------------------------------------------------
        # row parity
        # --------------------------------------------------
        if isinstance(canonical_row, dict):
            row_count = canonical_row.get("note_total_chart")
            if isinstance(row_count, int):
                if abs(row_count - len(events)) > max(50, int(len(events) * 0.2)):
                    warnings.append(_warn("L4_ROW", "row mismatch"))

        # --------------------------------------------------
        # degraded mode
        # --------------------------------------------------
        degraded_mode = True
        warnings.append("Lanota tips not enabled (Phase 3 only)")

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
            "radial_geometry": True,
            "canonical_kinds": list(CANONICAL_KINDS),
            "tips_supported": False,
        }


__all__ = ["LanotaValidator"]