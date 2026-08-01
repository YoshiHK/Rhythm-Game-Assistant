#!/usr/bin/env python3
from __future__ import annotations

"""
validator_d4dj.py (FULL REPLACEMENT - v2 normalized)

Phase 3 validator for D4DJ.

Scope:
- canonical payload validation
- lane-based structural consistency
- hold/flick/tap mapping validation

D4DJ is Phase-4 ready:
→ deterministic gameplay mapping ✅
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
GAME_ID = "d4dj"

CANONICAL_KINDS = {
    "tap",
    "flick_arrow",
    "hold_body_or_start",
    "hold_path",
}


def _err(code: str, msg: str) -> str:
    return f"{code}: {msg}"


def _warn(code: str, msg: str) -> str:
    return f"{code}: {msg}"


# ---------------------------------------------------------------------
class D4DJValidator(BaseValidatorV2):
    game_id = GAME_ID
    validator_id = "validator_d4dj"

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

        identity = self.resolve_identity_fields(
            canonical_payload,
            canonical_row,
        )

        # --------------------------------------------------
        # Identity
        # --------------------------------------------------
        if not identity["chart_id"]:
            errors.append(_err("D0_CHART", "missing chart_id"))

        # --------------------------------------------------
        # chart_meta
        # --------------------------------------------------
        chart_meta = canonical_payload.get("chart_meta")
        if not isinstance(chart_meta, dict):
            errors.append(_err("D1_META", "chart_meta must be dict"))
            chart_meta = {}

        max_tb = safe_float(chart_meta.get("max_time_beats"))
        if max_tb is None or max_tb < 0:
            errors.append(_err("D1_TIME", "invalid max_time_beats"))

        # --------------------------------------------------
        # note_events
        # --------------------------------------------------
        events = canonical_payload.get("note_events")
        if not isinstance(events, list):
            errors.append(_err("D2_EVENTS", "note_events must be list"))
            events = []

        if not events:
            errors.append(_err("D2_EMPTY", "note_events empty"))

        prev_tb: Optional[float] = None

        for i, ev in enumerate(events):
            if not isinstance(ev, dict):
                errors.append(_err("D2_TYPE", f"event[{i}] invalid"))
                continue

            tb = safe_float(ev.get("time_beats"))
            lane = ev.get("lane")
            kind = ev.get("kind")
            extra = ev.get("extra")

            # time
            if tb is None:
                errors.append(_err("D2_TIME", "missing time"))
            else:
                if tb < 0:
                    errors.append(_err("D2_TIME_NEG", "negative time"))
                if prev_tb is not None and tb < prev_tb:
                    errors.append(_err("D2_ORDER", "time not monotonic"))
                prev_tb = tb

            # lane
            if not isinstance(lane, int):
                errors.append(_err("D2_LANE", "invalid lane"))
            elif lane < 0:
                errors.append(_err("D2_LANE_NEG", "lane negative"))

            # kind
            if kind not in CANONICAL_KINDS:
                errors.append(_err("D2_KIND", f"{kind} invalid"))

            # extra
            if not isinstance(extra, dict):
                errors.append(_err("D2_EXTRA", "extra must be dict"))
                continue

            # hold consistency
            if kind == "hold_body_or_start":
                dur = safe_float(extra.get("duration_seconds"), 0.0)
                if dur is None or dur < 0:
                    errors.append(_err("D3_HOLD", "invalid duration"))

            # flick detection sanity
            if kind == "flick_arrow":
                if "scratch_side" not in extra:
                    warnings.append(_warn("D3_FLICK", "missing scratch_side"))

        # --------------------------------------------------
        # Row parity
        # --------------------------------------------------
        if isinstance(canonical_row, dict):
            rc = canonical_row.get("note_total_chart")
            if isinstance(rc, int):
                if abs(rc - len(events)) > max(50, int(len(events)*0.2)):
                    warnings.append(_warn("D4_ROW", "row mismatch"))

        # --------------------------------------------------
        # D4DJ tips supported ✅
        # --------------------------------------------------
        degraded_mode = False

        if errors:
            return build_validation_fail(errors=errors, warnings=warnings, degraded_mode=degraded_mode)

        return build_validation_ok(warnings=warnings, degraded_mode=degraded_mode)

    def capabilities(self) -> dict:
        return {
            "note_model": "lane_based",
            "canonical_kinds": list(CANONICAL_KINDS),
            "tips_supported": True,
            "supports_soflan": True,
        }


__all__ = ["D4DJValidator"]