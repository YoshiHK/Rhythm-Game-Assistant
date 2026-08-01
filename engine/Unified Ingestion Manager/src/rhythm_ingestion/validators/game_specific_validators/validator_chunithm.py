#!/usr/bin/env python3
from __future__ import annotations

"""
ChunithmValidator (UMI Phase 3)

Validates:
- canonical_row minimal sanity
- canonical_payload structural integrity
- basic CHUNITHM payload identity fields
- note_events timing / lane / kind / required extra fields
- BPM / bpm_changes sanity
- soft row/payload count parity

This validator is Phase-3 wiring only:
- No gameplay difficulty inference
- No tips logic
- No Phase 4 execution
"""

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from ..base_validator_v2 import BaseValidatorV2
from ..common_validator_utils import (
    safe_int,
    safe_float,
    compute_delta,
    is_within_threshold,
    values_equal,
    build_validation_ok,
    build_validation_fail,
)


# Keep existing validator-side allowed kinds to avoid intrusive contract changes.
# (Schema/validator parity can still be reviewed separately.)
_ALLOWED_KINDS = {
    "tap",
    "critical_tap",
    "flick_arrow",
    "hold_path",
}

_ALLOWED_DIFFICULTIES = {
    "BASIC",
    "ADVANCED",
    "EXPERT",
    "MASTER",
    "ULTIMA",
}


def _first_nonempty_str(*values: Any) -> Optional[str]:
    for v in values:
        if isinstance(v, str):
            s = v.strip()
            if s:
                return s
    return None


def _normalize_difficulty(value: Any) -> Optional[str]:
    if not isinstance(value, str):
        return None
    s = value.strip()
    if not s:
        return None
    return s.upper()


def _infer_title_from_path(path_value: Any) -> Optional[str]:
    if not isinstance(path_value, str):
        return None
    try:
        p = Path(path_value)
        stem = p.stem.strip()
        return stem or None
    except Exception:
        return None


def _coerce_payload_and_row(
    payload: Optional[Dict[str, Any]] = None,
    *,
    canonical_payload: Optional[Dict[str, Any]] = None,
    canonical_row: Optional[Dict[str, Any]] = None,
) -> Tuple[Dict[str, Any], Dict[str, Any], str]:
    """
    Supports:
    A) validate(raw_chart=..., canonical_payload=..., canonical_row=...)
    B) validate({"canonical_payload": ..., "canonical_row": ...})
    C) validate(canonical_payload_only_dict)
    """
    if canonical_payload is None and canonical_row is None and isinstance(payload, dict):
        canonical_payload = payload.get("canonical_payload") or payload
        canonical_row = payload.get("canonical_row") or payload
        input_kind = "canonical_row" if "canonical_payload" in payload or "canonical_row" in payload else "canonical_payload"
    else:
        input_kind = "explicit"

    if not isinstance(canonical_payload, dict):
        canonical_payload = {}

    if not isinstance(canonical_row, dict):
        canonical_row = {}

    return canonical_payload, canonical_row, input_kind

class ChunithmValidator(BaseValidatorV2):
    game_id = "chunithm"
    validator_id = "validator_chunithm"

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
        # BPM
        # --------------------------------------------------
        bpm = safe_float(chart_meta.get("bpm"))
        if bpm is None or bpm <= 0:
            errors.append("chart_meta.bpm must be > 0")

        # --------------------------------------------------
        # Note validation
        # --------------------------------------------------
        prev_t = -1.0

        for idx, ev in enumerate(note_events):
            if not isinstance(ev, dict):
                errors.append(f"note_events[{idx}] must be dict")
                continue

            tb = safe_float(ev.get("time_beats"))
            lane = safe_int(ev.get("lane"))
            kind = ev.get("kind")

            if tb is None or tb < 0:
                errors.append(f"note_events[{idx}] invalid time_beats")
            else:
                if tb < prev_t:
                    errors.append("note_events not sorted")
                prev_t = tb

            if lane is None or lane <= 0:
                errors.append(f"note_events[{idx}] invalid lane")

            if kind not in {"tap", "critical_tap", "flick_arrow", "hold_path"}:
                errors.append(f"invalid kind {kind}")

        # --------------------------------------------------
        # Final
        # --------------------------------------------------
        if errors:
            return self.fail_result(errors=errors, warnings=warnings)

        return self.ok_result(warnings=warnings)

__all__ = ["ChunithmValidator"]