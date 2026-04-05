#!/usr/bin/env python3
"""validator_ユメステ.py

UMI Phase 3 validator for ユメステ (夢のステラリウム / YMST).

Scope:
- Validate canonical payloads emitted by adapter_ユメステ.py
- Enforce hard invariants derived from Ched / YMST timing & note rules
- Perform NO mutation, NO enrichment (validator-only responsibility)

This is content-side work and does not modify completed UMI phases.
"""

from __future__ import annotations

from typing import Any, Dict, List

from .base_validator import BaseValidator


class ユメステValidator(BaseValidator):
    """Validator for YMST canonical payloads."""

    game_id = "yumesute"

    # ----------------------------
    # Entry point
    # ----------------------------

    def validate(
        self,
        *,
        raw_chart: Any,
        canonical_payload: Dict[str, Any],
        canonical_row: Dict[str, Any],
    ) -> Dict[str, Any]:
        errors: List[str] = []
        warnings: List[str] = []
        degraded = False

        # ----------------------------
        # Basic structure checks
        # ----------------------------

        note_events = canonical_payload.get("note_events")
        if not isinstance(note_events, list) or not note_events:
            errors.append("note_events must be a non-empty list")
        else:
            for i, ev in enumerate(note_events):
                if not isinstance(ev, dict):
                    errors.append(f"note_events[{i}] is not a dict")
                    continue
                if "time_beats" not in ev:
                    errors.append(f"note_events[{i}] missing time_beats")
                if "lane" not in ev:
                    errors.append(f"note_events[{i}] missing lane")
                if "kind" not in ev:
                    errors.append(f"note_events[{i}] missing kind")

        # ----------------------------
        # chart_meta checks
        # ----------------------------

        chart_meta = canonical_payload.get("chart_meta") or {}

        bpm = chart_meta.get("bpm")
        if bpm is None or not isinstance(bpm, (int, float)) or bpm <= 0:
            errors.append("chart_meta.bpm must be a positive number")

        bpm_changes = chart_meta.get("bpm_changes")
        if bpm_changes:
            if not isinstance(bpm_changes, list):
                errors.append("chart_meta.bpm_changes must be a list")
            else:
                # Must start at time 0
                first = bpm_changes[0]
                if not isinstance(first, dict) or first.get("time_beats") != 0:
                    errors.append("First bpm_changes entry must start at time_beats == 0")

        # ----------------------------
        # YMST-specific invariants
        # ----------------------------

        # Lane must be positive integer (YMST lanes are discrete, lane_offset applied in adapter)
        for i, ev in enumerate(note_events or []):
            lane = ev.get("lane")
            if not isinstance(lane, int) or lane <= 0:
                errors.append(f"note_events[{i}].lane must be a positive integer")

        # time_beats must be non-negative and monotonic
        last_time = -1.0
        for i, ev in enumerate(note_events or []):
            tb = ev.get("time_beats")
            if not isinstance(tb, (int, float)):
                errors.append(f"note_events[{i}].time_beats must be numeric")
                continue
            if tb < 0:
                errors.append(f"note_events[{i}].time_beats must be >= 0")
            if tb < last_time:
                warnings.append("note_events are not strictly time-ordered")
                degraded = True
            last_time = tb

        # ----------------------------
        # Hold / scratch structural sanity
        # ----------------------------

        # Ensure hold_end never appears before hold_start on same lane
        active_holds = {}
        for i, ev in enumerate(note_events or []):
            kind = ev.get("kind")
            lane = ev.get("lane")
            raw_type = (ev.get("extra") or {}).get("raw_type")

            if raw_type in ("hold_start", "hold_start_critical"):
                if lane in active_holds:
                    warnings.append(f"Multiple hold starts without end on lane {lane}")
                    degraded = True
                active_holds[lane] = ev.get("time_beats")

            elif raw_type == "hold_end":
                if lane not in active_holds:
                    errors.append(f"Hold end without start on lane {lane}")
                else:
                    del active_holds[lane]

        if active_holds:
            errors.append(f"Unclosed holds detected on lanes: {sorted(active_holds.keys())}")

        # ----------------------------
        # Row-level sanity
        # ----------------------------

        note_total_chart = canonical_row.get("note_total_chart")
        if note_total_chart is None or not isinstance(note_total_chart, int) or note_total_chart <= 0:
            warnings.append("canonical_row.note_total_chart is missing or non-positive")
            degraded = True

        # ----------------------------
        # Finalize
        # ----------------------------

        if errors:
            return self.fail(
                errors=errors,
                warnings=warnings,
                degraded_mode=degraded,
            )

        return self.ok(
            warnings=warnings,
            degraded_mode=degraded,
        )

    # ----------------------------
    # Capabilities
    # ----------------------------

    def capabilities(self) -> dict:
        return {
            "note_model": "lane_based",
            "supports_variable_bpm": True,
            "supports_sections": False,
            "enforces_hold_integrity": True,
        }


__all__ = ["ユメステValidator"]
