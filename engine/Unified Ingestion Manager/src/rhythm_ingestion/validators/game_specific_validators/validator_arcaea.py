#!/usr/bin/env python3
from __future__ import annotations

"""
validator_arcaea.py (FULL REPLACEMENT - v2 normalized)

UMI Phase 3 validator for Arcaea.

Responsibilities
----------------
- canonical_row sanity
- canonical_payload.note_events structural integrity
- adapter-grounded validation against parsed Chart
- optional section-level validation using section boundaries when present
- optional DB-backed / adapter-metadata parity checks

This validator is validation-only:
- no gameplay inference
- no payload mutation
- no Phase 4 execution
- no verification logic
"""

from typing import Any, Dict, List, Optional, Tuple

from ..base_validator_v2 import BaseValidatorV2
from ..common_validator_utils import (
    safe_int,
    safe_float,
    compute_delta,
    is_within_threshold,
    values_equal,
)


# --------------------------------------------------
# Arcaea adapter helper imports
# --------------------------------------------------
# Keep import flexible because exact module placement may differ.
try:
    from ..adapter_arcaea import (  # type: ignore
        load_chart,
        validate_note_events,
        build_sections_from_boundaries,
    )
except Exception:
    try:
        from ...adapters.game_specific_adapters.adapter_arcaea import (  # type: ignore
            load_chart,
            validate_note_events,
            build_sections_from_boundaries,
        )
    except Exception as e:  # pragma: no cover
        raise ImportError(
            "Arcaea validator could not import load_chart / validate_note_events / "
            "build_sections_from_boundaries from adapter_arcaea."
        ) from e


# --------------------------------------------------
# Constants
# --------------------------------------------------
GAME_ID = "arcaea"

# Allowed canonical kinds aligned to adapter_arcaea full-replacement output.
CANONICAL_KINDS = {
    "tap",
    "critical_tap",
    "flick_arrow",
    "hold_body_or_start",
    "hold_path",
}

# Raw types that contribute directly to combo in adapter diagnostics
COMBO_RAW_TYPES = {
    "tap",
    "arctap",
    "flick",
    "hold_start",
    "hold_end",
}


def _err(code: str, message: str) -> str:
    return f"{code}: {message}"


def _warn(code: str, message: str) -> str:
    return f"{code}: {message}"


class ArcaeaValidator(BaseValidatorV2):
    game_id = GAME_ID
    validator_id = "validator_arcaea"

    def validate_v2(
        self,
        payload: Dict[str, Any],
        *,
        raw_chart: Any = None,
        canonical_payload: Optional[Dict[str, Any]] = None,
        canonical_row: Optional[Dict[str, Any]] = None,
        **context: Any,
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
        diagnostics["resolved_game"] = resolved["game"]
        diagnostics["resolved_chart_id"] = resolved["chart_id"]
        diagnostics["resolved_title"] = resolved["title"]
        diagnostics["resolved_difficulty"] = resolved["difficulty"]

        # --------------------------------------------------
        # 1) Identity (STRICT)
        # --------------------------------------------------
        if not resolved["game"]:
            errors.append(_err("A0_GAME_MISSING", "missing required field: game"))

        if not resolved["chart_id"]:
            errors.append(_err("A0_CHART_ID_MISSING", "missing required field: chart_id"))

        if not resolved["difficulty"]:
            errors.append(_err("A0_DIFFICULTY_MISSING", "missing required field: difficulty"))

        # title may degrade safely if path-based fallback was incomplete
        if not resolved["title"]:
            warnings.append(_warn("A0_TITLE_MISSING", "missing title"))

        if resolved["game"] and resolved["game"] != self.game_id:
            errors.append(
                _err(
                    "A0_GAME_MISMATCH",
                    f"game must be '{self.game_id}', got {resolved['game']!r}",
                )
            )

        # --------------------------------------------------
        # 2) Row-level sanity
        # --------------------------------------------------
        if isinstance(canonical_row, dict) and canonical_row:
            row_game = canonical_row.get("game_id", canonical_row.get("game"))
            if row_game is not None and row_game != self.game_id:
                errors.append(
                    _err(
                        "A0_ROW_GAME_MISMATCH",
                        f"canonical_row game must be '{self.game_id}', got {row_game!r}",
                    )
                )

            ntc = canonical_row.get("note_total_chart")
            if ntc is None:
                errors.append(_err("A0_ROW_NOTE_TOTAL_MISSING", "canonical_row['note_total_chart'] missing"))
            else:
                ntc_int = safe_int(ntc, default=None)
                if ntc_int is None or ntc_int < 0:
                    errors.append(
                        _err(
                            "A0_ROW_NOTE_TOTAL_INVALID",
                            f"canonical_row['note_total_chart'] must be a non-negative int, got {ntc!r}",
                        )
                    )

            dur = canonical_row.get("duration_ms")
            if dur is None:
                warnings.append(_warn("A0_ROW_DURATION_MISSING", "canonical_row['duration_ms'] missing"))
            else:
                dur_int = safe_int(dur, default=None)
                if dur_int is None or dur_int < 0:
                    errors.append(
                        _err(
                            "A0_ROW_DURATION_INVALID",
                            f"canonical_row['duration_ms'] must be a non-negative int, got {dur!r}",
                        )
                    )

        # --------------------------------------------------
        # 3) Payload structure
        # --------------------------------------------------
        note_events = canonical_payload.get("note_events")
        if not isinstance(note_events, list) or not note_events:
            errors.append(_err("A1_NOTE_EVENTS_TYPE", "canonical_payload['note_events'] must be a non-empty list"))
            note_events = []

        chart_meta = canonical_payload.get("chart_meta")
        if not isinstance(chart_meta, dict):
            errors.append(_err("A1_CHART_META_TYPE", "canonical_payload['chart_meta'] must be a dict"))
            chart_meta = {}

        payload_game = canonical_payload.get("game_id")
        if payload_game not in (None, self.game_id):
            errors.append(
                _err(
                    "A1_PAYLOAD_GAME_MISMATCH",
                    f"canonical_payload['game_id'] mismatch: expected '{self.game_id}', got {payload_game!r}",
                )
            )

        diagnostics["note_events_present"] = isinstance(canonical_payload.get("note_events"), list)
        diagnostics["chart_meta_present"] = isinstance(canonical_payload.get("chart_meta"), dict)

        # Optional schema-level kind sanity before expensive ground-truth validation
        prev_tb = -1.0
        for idx, ev in enumerate(note_events):
            if not isinstance(ev, dict):
                errors.append(_err("A1_EVENT_TYPE", f"note_events[{idx}] must be dict"))
                continue

            tb = safe_float(ev.get("time_beats"), default=None)
            lane = safe_int(ev.get("lane"), default=None)
            kind = ev.get("kind")
            extra = ev.get("extra")

            if tb is None:
                errors.append(_err("A1_TIME_TYPE", f"note_events[{idx}].time_beats must be numeric"))
            else:
                if tb < 0:
                    errors.append(_err("A1_TIME_NEGATIVE", f"note_events[{idx}].time_beats must be >= 0"))
                if tb < prev_tb:
                    errors.append(
                        _err(
                            "A1_TIME_MONOTONIC",
                            f"note_events[{idx}].time_beats={tb} is less than previous time_beats={prev_tb}",
                        )
                    )
                prev_tb = tb

            # Arcaea arcs/free flicks may use lane=0; reject only missing / negative
            if lane is None:
                errors.append(_err("A1_LANE_TYPE", f"note_events[{idx}].lane must be int"))
            elif lane < 0:
                errors.append(_err("A1_LANE_INVALID", f"note_events[{idx}].lane must be >= 0"))

            if not isinstance(kind, str):
                errors.append(_err("A1_KIND_TYPE", f"note_events[{idx}].kind must be str"))
            elif kind not in CANONICAL_KINDS:
                errors.append(
                    _err(
                        "A1_KIND_INVALID",
                        f"note_events[{idx}].kind={kind!r} not allowed (expected one of {sorted(CANONICAL_KINDS)})",
                    )
                )

            if not isinstance(extra, dict):
                errors.append(_err("A1_EXTRA_TYPE", f"note_events[{idx}].extra must be dict"))
                continue

            raw_type = extra.get("raw_type")
            if not isinstance(raw_type, str):
                warnings.append(_warn("A1_RAW_TYPE_MISSING", f"note_events[{idx}].extra.raw_type missing"))

        # If row/payload basics already failed badly, stop cleanly
        if errors and not note_events:
            return self.fail_result(
                errors=errors,
                warnings=warnings,
                degraded_mode=bool(warnings),
                diagnostics=diagnostics,
            )

        # --------------------------------------------------
        # 4) Ground-truth validation using Arcaea Chart model
        # --------------------------------------------------
        chart = None

        # raw_chart may already be a Chart object
        if raw_chart is not None:
            try:
                chart = load_chart(raw_chart)
            except Exception:
                chart = None

        # Fallback to source path in adapter_metadata / payload / row
        if chart is None:
            adapter_meta = canonical_payload.get("adapter_metadata")
            if not isinstance(adapter_meta, dict):
                adapter_meta = {}

            src = (
                adapter_meta.get("source_path")
                or canonical_payload.get("source_ref")
                or canonical_row.get("chart_path")
            )

            if isinstance(src, str) and src:
                try:
                    chart = load_chart(src)
                except Exception:
                    chart = None

        if chart is None:
            errors.append(
                _err(
                    "A2_CHART_UNAVAILABLE",
                    "Cannot obtain Arcaea Chart for validation (raw_chart not loadable and no usable source path).",
                )
            )
            return self.fail_result(
                errors=errors,
                warnings=warnings,
                degraded_mode=bool(warnings),
                diagnostics=diagnostics,
            )

        # 4.1 Full-chart note_events validation
        rep = self._run_report(
            validate_note_events(chart, note_events),
            label="validate_note_events",
        )
        diagnostics["ground_truth_note_report_ok"] = rep["ok"]
        if not rep["ok"]:
            errors.extend(rep["errors"])
            return self.fail_result(
                errors=errors,
                warnings=warnings,
                degraded_mode=bool(warnings),
                diagnostics=diagnostics,
            )

        # 4.2 Optional: section-level validation if sections provide ms boundaries
        sections = canonical_payload.get("sections")
        rep2 = self._validate_sections_against_chart(
            chart=chart,
            note_events=note_events,
            sections=sections,
        )
        diagnostics["section_report_ok"] = rep2["ok"]
        if not rep2["ok"]:
            errors.extend(rep2["errors"])
            return self.fail_result(
                errors=errors,
                warnings=warnings,
                degraded_mode=bool(warnings),
                diagnostics=diagnostics,
            )

        # --------------------------------------------------
        # 5) Optional row/payload parity checks
        # --------------------------------------------------
        adapter_meta = canonical_payload.get("adapter_metadata")
        if not isinstance(adapter_meta, dict):
            adapter_meta = {}

        diff_cons = adapter_meta.get("difficulty_consistency")
        if not isinstance(diff_cons, dict):
            diff_cons = {}

        diff_details = adapter_meta.get("difficulty_details")
        if not isinstance(diff_details, dict):
            diff_details = {}

        chart_total_combo = diff_cons.get("chart_total_combo")
        row_combo = canonical_row.get("note_total_chart")

        eq = values_equal(chart_total_combo, row_combo)
        if eq is False:
            errors.append(
                _err(
                    "A3_ROW_PAYLOAD_COMBO_MISMATCH",
                    "Row/payload combo mismatch: "
                    f"adapter_metadata.difficulty_consistency.chart_total_combo={chart_total_combo} "
                    f"!= canonical_row['note_total_chart']={row_combo}.",
                )
            )

        # Optional DB-backed threshold check
        note_total_db = canonical_row.get("note_total_db")
        if note_total_db is None:
            note_total_db = diff_details.get("note_total_db")

        threshold = diff_cons.get("note_delta_threshold")

        if isinstance(row_combo, int) and isinstance(note_total_db, int) and isinstance(threshold, int):
            d = compute_delta(row_combo, note_total_db)
            within = is_within_threshold(d, threshold)
            diagnostics["db_note_delta"] = d
            if within is False:
                errors.append(
                    _err(
                        "A3_DB_NOTE_DELTA_EXCEEDED",
                        f"DB-backed delta exceeds threshold: |note_total_chart - note_total_db|={d} > {threshold}.",
                    )
                )

        # --------------------------------------------------
        # 6) Final
        # --------------------------------------------------
        diagnostics["note_event_count"] = len(note_events)
        diagnostics["row_shape_present"] = bool(canonical_row)

        if errors:
            return self.fail_result(
                errors=errors,
                warnings=warnings,
                degraded_mode=bool(warnings),
                diagnostics=diagnostics,
            )

        return self.ok_result(
            warnings=warnings,
            degraded_mode=bool(warnings),
            diagnostics=diagnostics,
        )

    def validate_row(self, canonical_row: Dict[str, Any]) -> dict:
        return self.validate(canonical_row=canonical_row)

    def capabilities(self) -> dict:
        return {
            "note_model": "hybrid_ground_arc",
            "supports_sections": True,
            "supports_ground_truth_validation": True,
            "supports_variable_bpm": True,
            "supports_db_parity": True,
        }

    # ----------------------------
    # Internal helpers
    # ----------------------------
    @staticmethod
    def _run_report(report: Any, *, label: str) -> Dict[str, Any]:
        """
        Normalize different report dict shapes into:
          { ok: bool, errors: list[str] }
        """
        if not isinstance(report, dict):
            return {
                "ok": False,
                "errors": [f"{label}: report is not a dict ({type(report).__name__})."],
            }

        ok = bool(report.get("ok"))
        errs = report.get("errors") or []
        if not isinstance(errs, list):
            errs = [f"{label}: report.errors is not a list ({type(errs).__name__})."]
            ok = False

        errs2: List[str] = []
        for e in errs:
            if isinstance(e, str):
                errs2.append(e)
            else:
                errs2.append(f"{label}: non-string error entry ({type(e).__name__}).")

        return {"ok": ok, "errors": errs2}

    @staticmethod
    def _section_boundaries_ms(sections: Any) -> List[int]:
        """
        Extract section end boundaries in ms from sections list.

        Supports:
        - sections[*]['end_ms'] if present
        - otherwise returns [] (skip section validation)
        """
        if not isinstance(sections, list) or not sections:
            return []

        boundaries: List[int] = []
        for s in sections:
            if not isinstance(s, dict):
                continue
            end_ms = s.get("end_ms")
            if isinstance(end_ms, int) and end_ms > 0:
                boundaries.append(end_ms)

        return sorted(set(boundaries))

    def _validate_sections_against_chart(
        self,
        *,
        chart: Any,
        note_events: List[Dict[str, Any]],
        sections: Any,
    ) -> Dict[str, Any]:
        """
        Rebuild sections using the adapter helper and compare section-wise expected combo.

        This replaces the older dependency on validate_note_events_by_sections(...)
        so the validator stays aligned with the normalized Wave 6.1 adapter.
        """
        boundaries_ms = self._section_boundaries_ms(sections)
        if not boundaries_ms:
            return {"ok": True, "errors": []}

        if not isinstance(sections, list):
            return {
                "ok": False,
                "errors": ["sections must be a list when section boundaries are present."],
            }

        rebuilt = build_sections_from_boundaries(
            chart,
            note_events,
            boundaries_ms,
        )

        if not isinstance(rebuilt, list):
            return {
                "ok": False,
                "errors": ["build_sections_from_boundaries did not return a list."],
            }

        original_end_to_expected: Dict[int, int] = {}
        for s in sections:
            if not isinstance(s, dict):
                continue
            end_ms = s.get("end_ms")
            expected_total_combo = s.get("expected_total_combo")
            if isinstance(end_ms, int) and isinstance(expected_total_combo, int):
                original_end_to_expected[end_ms] = expected_total_combo

        errors: List[str] = []
        for rs in rebuilt:
            if not isinstance(rs, dict):
                continue
            end_ms = rs.get("end_ms")
            rebuilt_expected = rs.get("expected_total_combo")
            if isinstance(end_ms, int) and isinstance(rebuilt_expected, int):
                original_expected = original_end_to_expected.get(end_ms)
                if original_expected is not None and original_expected != rebuilt_expected:
                    errors.append(
                        "Section combo mismatch at "
                        f"end_ms={end_ms}: original expected_total_combo={original_expected}, "
                        f"rebuilt expected_total_combo={rebuilt_expected}."
                    )

        return {"ok": len(errors) == 0, "errors": errors}


__all__ = ["ArcaeaValidator"]