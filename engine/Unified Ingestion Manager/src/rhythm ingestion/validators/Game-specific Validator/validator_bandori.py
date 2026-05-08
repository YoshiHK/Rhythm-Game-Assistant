#!/usr/bin/env python3
"""
BandoriValidator

Game-specific validator for Bandori charts.
Phase: UMI Phase 3 (validation only).

Responsibilities:
- Structural validation of canonical payload
- Consistency checks between payload and canonical row
- Degraded-mode signaling (no hard gameplay inference)

Non-goals:
- No tips logic
- No element inference
- No personalization execution
"""

from __future__ import annotations

from typing import Any, Dict, List

from .base_validator import BaseValidator
from .common_validator_utils import (
    safe_int,
    safe_float,
    build_validation_ok,
    build_validation_fail,
    compute_phase4_gate_state,
    explain_gate_failures,
)


class BandoriValidator(BaseValidator):
    game_id = "bandori"

    # ------------------------------------------------------------------
    # Required interface
    # ------------------------------------------------------------------

    def validate(
        self,
        *,
        raw_chart: Any,
        canonical_payload: Dict[str, Any],
        canonical_row: Dict[str, Any],
    ) -> dict:
        errors: List[str] = []
        warnings: List[str] = []

        # --------------------------------------------------------------
        # 1) Basic identity checks
        # --------------------------------------------------------------
        if canonical_payload.get("game_id") != self.game_id:
            errors.append(
                f"Invalid game_id: expected '{self.game_id}', "
                f"got '{canonical_payload.get('game_id')}'."
            )

        # --------------------------------------------------------------
        # 2) note_events validation (hard requirement)
        # --------------------------------------------------------------
        note_events = canonical_payload.get("note_events")
        if not isinstance(note_events, list):
            errors.append("canonical_payload['note_events'] must be a list.")
        elif not note_events:
            errors.append("canonical_payload['note_events'] must not be empty.")

        # --------------------------------------------------------------
        # 3) chart_meta validation
        # --------------------------------------------------------------
        chart_meta = canonical_payload.get("chart_meta")
        if not isinstance(chart_meta, dict):
            errors.append("canonical_payload['chart_meta'] must be a dict.")
        else:
            bpm = safe_float(chart_meta.get("bpm"))
            if bpm is None or bpm <= 0:
                errors.append("chart_meta.bpm must be a positive number.")

            max_beats = safe_float(chart_meta.get("max_time_beats"))
            if max_beats is None or max_beats <= 0:
                errors.append("chart_meta.max_time_beats must be positive.")

        # --------------------------------------------------------------
        # 4) Canonical row consistency (soft checks)
        # --------------------------------------------------------------
        row_level = safe_int(canonical_row.get("level"))
        if row_level is None or row_level <= 0:
            warnings.append("canonical_row.level is missing or invalid.")

        difficulty_label = canonical_row.get("difficulty_label")
        if not difficulty_label:
            warnings.append("canonical_row.difficulty_label is missing.")

        # --------------------------------------------------------------
        # 5) Optional sections (degraded mode if absent)
        # --------------------------------------------------------------
        degraded_mode = False
        if "sections" not in canonical_payload:
            degraded_mode = True
            warnings.append(
                "No sections present; tips quality may be reduced."
            )

        # --------------------------------------------------------------
        # 6) Phase‑4 gate awareness (informational only)
        # --------------------------------------------------------------
        gate = compute_phase4_gate_state(
            engine_mode=canonical_payload.get("engine_mode"),
            feature_flags=canonical_payload.get("feature_flags"),
            opt_in=canonical_payload.get("opt_in"),
        )

        if not gate["personalization_allowed"]:
            degraded_mode = True
            explanation = explain_gate_failures(gate["gate_fail_reasons"])
            if explanation:
                warnings.append(explanation)

        # --------------------------------------------------------------
        # 7) Final decision
        # --------------------------------------------------------------
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

    # ------------------------------------------------------------------
    # Optional v2 interfaces
    # ------------------------------------------------------------------

    def capabilities(self) -> dict:
        return {
            "note_model": "lane_based",
            "supports_sections": True,
            "supports_variable_bpm": True,
            "supports_slides": True,
        }

    def explain_failure(self, result: dict) -> str:
        if not result.get("supported"):
            return "Bandori chart failed structural validation."
        if result.get("degraded_mode"):
            return "Bandori chart is valid but runs in degraded mode."
        return ""
