#!/usr/bin/env python3
from __future__ import annotations

"""
validator_maimai.py (FULL REPLACEMENT - v2 normalized)

UMI Phase 3 validator for maimai.

Scope:
- canonical payload structural validation
- canonical note_events validation
- chart_meta consistency checks
- adapter alignment checks

Policy:
- structural errors → errors
- maimai specific issues → warnings
- tips not supported → degraded_mode=True
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
GAME_ID = "maimai"

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
class MaimaiValidator(BaseValidatorV2):
    game_id = GAME_ID
    validator_id = "validator_maimai"

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

        resolved = self.resolve_identity_fields(
            canonical_payload,
            canonical_row,
        )

        # --------------------------------------------------
        # Identity
        # --------------------------------------------------
        if not resolved["game"]:
            errors.append(_err("M0_GAME", "missing game"))

        if resolved["game"] and resolved["game"] != self.game_id:
            errors.append(_warn("M0_GAME_MISMATCH", f"expected {self.game_id}, got {resolved['game']}"))

        if not resolved["chart_id"]:
            errors.append(_err("M0_CHART_ID", "missing chart_id"))

        if not resolved["difficulty"]:
            warnings.append(_warn("M0_DIFFICULTY", "missing difficulty"))

        # --------------------------------------------------
        # chart_meta
        # --------------------------------------------------
        chart_meta = canonical_payload.get("chart_meta")
        if not isinstance(chart_meta, dict):
            errors.append(_err("M1_META", "chart_meta must be dict"))
            chart_meta = {}

        bpm = safe_float(chart_meta.get("bpm"))
        if bpm is not None and bpm <= 0:
            warnings.append(_warn("M1_BPM", "bpm non-positive"))

        max_tb = safe_float(chart_meta.get("max_time_beats"))
        if max_tb is None or max_tb < 0:
            errors.append(_err("M1_MAX_BEATS", "max_time_beats invalid"))

        max_ms = chart_meta.get("max_time_ms")
        if max_ms is not None:
            if safe_int(max_ms) is None:
                errors.append(_err("M1_MAX_MS", "max_time_ms invalid"))

        # bpm changes check
        bpm_changes = chart_meta.get("bpm_changes")
        if bpm_changes is not None and not isinstance(bpm_changes, list):
            errors.append(_err("M1_BPM_CHANGES", "bpm_changes must be list"))

        # --------------------------------------------------
        # note_events
        # --------------------------------------------------
        events = canonical_payload.get("note_events")
        if not isinstance(events, list):
            errors.append(_err("M2_EVENTS", "note_events must be list"))
            events = []

        if not events:
            errors.append(_err("M2_EMPTY", "note_events empty"))

        prev_tb: Optional[float] = None

        for i, ev in enumerate(events):
            if not isinstance(ev, dict):
                errors.append(_err("M2_TYPE", f"event[{i}] not dict"))
                continue

            tb = safe_float(ev.get("time_beats"))
            lane = ev.get("lane")
            kind = ev.get("kind")
            extra = ev.get("extra")

            # time_beats
            if tb is None:
                errors.append(_err("M2_TIME", f"event[{i}] missing time_beats"))
            else:
                if tb < 0:
                    errors.append(_err("M2_TIME_NEG", "time_beats < 0"))
                if prev_tb is not None and tb < prev_tb:
                    errors.append(_err("M2_TIME_ORDER", "time not monotonic"))
                prev_tb = tb

            # lane (maimai: allow 0)
            if not isinstance(lane, int):
                errors.append(_err("M2_LANE", f"event[{i}] lane invalid"))

            # kind
            if not isinstance(kind, str):
                errors.append(_err("M2_KIND", f"event[{i}] invalid kind"))
            elif kind not in CANONICAL_KINDS:
                errors.append(_err("M2_KIND_UNKNOWN", f"{kind} not allowed"))

            # extra
            if not isinstance(extra, dict):
                errors.append(_err("M2_EXTRA", f"event[{i}] extra must be dict"))
                continue

            # soft maimai-specific checks
            if kind == "hold_body_or_start":
                if "duration_sec" not in extra:
                    warnings.append(_warn("M3_HOLD", "hold missing duration"))

            if kind == "hold_path":
                if "segments_total" not in extra:
                    warnings.append(_warn("M3_SLIDE", "slide missing segmentation info"))

        # --------------------------------------------------
        # row parity (soft)
        # --------------------------------------------------
        if isinstance(canonical_row, dict):
            row_count = canonical_row.get("note_total_chart")
            if isinstance(row_count, int):
                if abs(row_count - len(events)) > max(50, int(len(events) * 0.2)):
                    warnings.append(_warn("M4_ROW_MISMATCH", "row count mismatch"))

        # --------------------------------------------------
        # degraded mode
        # --------------------------------------------------
        degraded_mode = True
        warnings.append("maimai tips unsupported (Phase 3 only)")

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
            "note_model": "touch_radial",
            "supports_sections": False,
            "supports_variable_bpm": True,
            "canonical_kinds": list(CANONICAL_KINDS),
            "tips_supported": False,
        }


__all__ = ["MaimaiValidator"]