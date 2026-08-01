#!/usr/bin/env python3
from __future__ import annotations

"""
validator_dynamix.py (FULL REPLACEMENT - v2 normalized)

Phase 3 validator for Dynamix.

Scope:
- canonical payload validation
- 3-side structural consistency
- timing / hold integrity

No gameplay logic / no tips inference.
"""

from typing import Any, Dict, List, Optional

from ..base_validator_v2 import BaseValidatorV2
from ..common_validator_utils import (
    safe_int,
    safe_float,
    build_validation_ok,
    build_validation_fail,
)

# ---------------------------------------------------------------------
GAME_ID = "dynamix"

CANONICAL_KINDS = {
    "tap",
    "hold_body_or_start",
    "hold_path",
}


def _err(code: str, msg: str) -> str:
    return f"{code}: {msg}"


def _warn(code: str, msg: str) -> str:
    return f"{code}: {msg}"


# ---------------------------------------------------------------------
class DynamixValidator(BaseValidatorV2):
    game_id = GAME_ID
    validator_id = "validator_dynamix"

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

        canonical_payload, canonical_row, _ = self.coerce_payload_and_row(
            payload,
            canonical_payload=canonical_payload,
            canonical_row=canonical_row,
        )

        identity = self.resolve_identity_fields(
            canonical_payload,
            canonical_row,
        )

        # --------------------------------------------------
        # identity
        # --------------------------------------------------
        if not identity["chart_id"]:
            errors.append(_err("DY0_CHART", "missing chart_id"))

        # --------------------------------------------------
        # chart_meta
        # --------------------------------------------------
        chart_meta = canonical_payload.get("chart_meta")
        if not isinstance(chart_meta, dict):
            errors.append(_err("DY1_META", "chart_meta must be dict"))
            chart_meta = {}

        max_tb = safe_float(chart_meta.get("max_time_beats"))
        if max_tb is None or max_tb < 0:
            errors.append(_err("DY1_TIME", "invalid max_time_beats"))

        bpm = safe_float(chart_meta.get("bpm"))
        if bpm is None or bpm <= 0:
            warnings.append(_warn("DY1_BPM", "non-positive bpm"))

        # --------------------------------------------------
        # note_events
        # --------------------------------------------------
        events = canonical_payload.get("note_events")
        if not isinstance(events, list):
            errors.append(_err("DY2_EVENTS", "note_events must be list"))
            events = []

        if not events:
            errors.append(_err("DY2_EMPTY", "note_events empty"))

        prev_tb: Optional[float] = None

        for i, ev in enumerate(events):
            if not isinstance(ev, dict):
                errors.append(_err("DY2_TYPE", f"event[{i}] invalid"))
                continue

            tb = safe_float(ev.get("time_beats"))
            lane = ev.get("lane")
            kind = ev.get("kind")
            extra = ev.get("extra")

            # time
            if tb is None:
                errors.append(_err("DY2_TIME", "missing time"))
            else:
                if tb < 0:
                    errors.append(_err("DY2_TIME_NEG", "negative time"))
                if prev_tb is not None and tb < prev_tb:
                    errors.append(_err("DY2_ORDER", "time not monotonic"))
                prev_tb = tb

            # lane
            if not isinstance(lane, int):
                errors.append(_err("DY2_LANE", "invalid lane"))
            elif lane < 0:
                errors.append(_err("DY2_LANE_NEG", "lane negative"))

            # kind
            if kind not in CANONICAL_KINDS:
                errors.append(_err("DY2_KIND", f"{kind} not allowed"))

            # extra
            if not isinstance(extra, dict):
                errors.append(_err("DY2_EXTRA", "extra must be dict"))
                continue

            # soft geometry checks
            if "side" not in extra:
                warnings.append(_warn("DY3_SIDE", "missing side"))

            if "position" not in extra:
                warnings.append(_warn("DY3_POS", "missing position"))

            # hold consistency
            if kind == "hold_body_or_start":
                dur = safe_float(extra.get("duration_bars"), 0.0)
                if dur is None or dur < 0:
                    errors.append(_err("DY3_HOLD", "invalid duration"))

        # --------------------------------------------------
        # row parity
        # --------------------------------------------------
        if isinstance(canonical_row, dict):
            rc = canonical_row.get("note_total_chart")
            if isinstance(rc, int):
                if abs(rc - len(events)) > max(50, int(len(events)*0.2)):
                    warnings.append(_warn("DY4_ROW", "row mismatch"))

        # --------------------------------------------------
        # Dynamix tips NOT enabled
        # --------------------------------------------------
        degraded_mode = True

        if errors:
            return build_validation_fail(errors=errors, warnings=warnings, degraded_mode=degraded_mode)

        return build_validation_ok(warnings=warnings, degraded_mode=degraded_mode)

    def capabilities(self) -> dict:
        return {
            "note_model": "spatial_three_side",
            "supports_sides": True,
            "supports_width": True,
            "time_unit": "bars",
            "tips_supported": False,
        }


__all__ = ["DynamixValidator"]