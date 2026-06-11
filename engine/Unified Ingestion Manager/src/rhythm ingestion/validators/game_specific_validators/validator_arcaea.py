"""
ArcaeaValidator (UMI Phase 3)

UMI validator wrapper for Arcaea charts.

This validator:
- validates the canonical_row (minimal sanity checks)
- validates canonical_payload.note_events using Arcaea-native ground truth logic
- optionally validates per-section combo expectations if sections are present

It does NOT modify Phase 1/2 logic. It only raises on validation failures.

Note:
- This wrapper assumes your Arcaea adapter layer (or nearby module) provides:
    - validate_note_events(chart, note_events) -> report dict with keys: ok(bool), errors(list[str])
    - validate_note_events_by_sections(chart, note_events, section_boundaries_ms) -> report dict with ok/errors
  These functions are visible in your Arcaea codebase alongside adapter logic. [2](https://onedrive.live.com?cid=D5D62A1EF303BA22&id=D5D62A1EF303BA22!sddba83390cce4b54973b863db55e8c49)
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from .base_validator import BaseValidator
from .common_validator_utils import (
    compute_delta,
    is_within_threshold,
    values_equal,
)

# Import Arcaea-native helpers from your Arcaea adapter module.
# These functions are present in the Arcaea side code you attached. [2](https://onedrive.live.com?cid=D5D62A1EF303BA22&id=D5D62A1EF303BA22!sddba83390cce4b54973b863db55e8c49)
from .adapter_arcaea import (
    load_chart,  # load_chart(source_ref or Chart) -> Chart
    validate_note_events,  # validate_note_events(chart, note_events) -> report dict
    validate_note_events_by_sections,  # validate_note_events_by_sections(chart, note_events, boundaries_ms) -> report dict
)


class ArcaeaValidator(BaseValidator):
    game_id = "arcaea"

    def validate(
        self,
        *,
        raw_chart: Any,
        canonical_payload: Dict[str, Any],
        canonical_row: Dict[str, Any],
    ) -> None:
        errors: List[str] = []

        # 1) Row-level sanity checks (minimal, Phase-3 safe)
        self._validate_row_basic(canonical_row, errors)
        self._fail_if(errors, stage="row", song_id=canonical_row.get("song_id"))

        # 2) Payload structural sanity
        note_events = canonical_payload.get("note_events")
        if not isinstance(note_events, list) or not note_events:
            errors.append("canonical_payload['note_events'] must be a non-empty list for arcaea.")
            self._fail_if(errors, stage="payload", song_id=canonical_row.get("song_id"))
            self._validate_pattern_tags(...)
                        

        # 3) Ground-truth validation using Arcaea Chart model
        # raw_chart may already be a Chart (depending on adapter.load implementation).
        # load_chart will pass through if it's already Chart. [2](https://onedrive.live.com?cid=D5D62A1EF303BA22&id=D5D62A1EF303BA22!sddba83390cce4b54973b863db55e8c49)
        try:
            chart = load_chart(raw_chart)
        except Exception:
            # If raw_chart isn't usable here, fall back to source_path in adapter_metadata if present
            src = (canonical_payload.get("adapter_metadata") or {}).get("source_path")
            if isinstance(src, str) and src:
                chart = load_chart(src)
            else:
                errors.append("Cannot obtain Arcaea Chart for validation (raw_chart not loadable and no source_path).")
                self._fail_if(errors, stage="payload", song_id=canonical_row.get("song_id"))
            return

        # 3.1 Full-chart note_events validation
        rep = self._run_report(validate_note_events(chart, note_events), label="validate_note_events")
        if not rep["ok"]:
            errors.extend(rep["errors"])
            self._fail_if(errors, stage="note_events", song_id=canonical_row.get("song_id"))
            return

        # 3.2 Optional: section-level validation if sections provide ms boundaries
        sections = canonical_payload.get("sections")
        boundaries_ms = self._section_boundaries_ms(sections)
        if boundaries_ms:
            rep2 = self._run_report(
                validate_note_events_by_sections(chart, note_events, boundaries_ms),
                label="validate_note_events_by_sections",
            )
            if not rep2["ok"]:
                errors.extend(rep2["errors"])
                self._fail_if(errors, stage="sections", song_id=canonical_row.get("song_id"))
                return

        # 4) Optional: light parity check between row note_total_chart and adapter_metadata chart_total_combo
        # This is safe and non-invasive: only checks when both are present as ints.
        adapter_meta = canonical_payload.get("adapter_metadata") or {}
        diff_cons = adapter_meta.get("difficulty_consistency") or {}
        chart_total_combo = diff_cons.get("chart_total_combo")
        row_combo = canonical_row.get("note_total_chart")
        eq = values_equal(chart_total_combo, row_combo)
        if eq is False:
            errors.append(
                "Row/payload combo mismatch: "
                f"adapter_metadata.difficulty_consistency.chart_total_combo={chart_total_combo} "
                f"!= canonical_row['note_total_chart']={row_combo}."
            )

        # Optional: respect note_delta_threshold if provided, without changing strictness elsewhere
        # Only applies if note_total_db is present (from arcsong.json) and row combo exists.
        note_total_db = (adapter_meta.get("difficulty_details") or {}).get("note_total_db")
        threshold = diff_cons.get("note_delta_threshold")
        if isinstance(row_combo, int) and isinstance(note_total_db, int) and isinstance(threshold, int):
            d = compute_delta(row_combo, note_total_db)
            within = is_within_threshold(d, threshold)
            if within is False:
                errors.append(
                    f"DB-backed delta exceeds threshold: |note_total_chart - note_total_db|={d} > {threshold}."
                )

        self._fail_if(errors, stage="final", song_id=canonical_row.get("song_id"))

        from .common_validator_utils import (
            compute_phase4_gate_state,
            explain_gate_failures,
            build_validation_ok,
        )

        gate = compute_phase4_gate_state(
            engine_mode=canonical_payload.get("engine_mode"),
            feature_flags=canonical_payload.get("feature_flags"),
            opt_in=canonical_payload.get("opt_in"),
        )

        warnings = []
        degraded_mode = False

        if not gate["personalization_allowed"]:
            degraded_mode = True
            msg = explain_gate_failures(gate["gate_fail_reasons"])
            if msg:
                warnings.append(msg)

        return build_validation_ok(
            warnings=warnings,
            degraded_mode=degraded_mode,
        )

    
        def capabilities(self) -> dict:
            return {
                "note_model": "spatial",
                "supports_sections": True,
                "supports_ground_truth_validation": True,
                "supports_variable_bpm": True,
            }


    # ----------------------------
    # Internal helpers
    # ----------------------------

    @staticmethod
    def _fail_if(errors: List[str], *, stage: str, song_id: Any) -> None:
        if errors:
            raise ValueError(
                f"ArcaeaValidator ({stage}) failed for song_id={song_id!r}: " + "; ".join(errors)
            )

    @staticmethod
    def _validate_row_basic(canonical_row: Dict[str, Any], errors: List[str]) -> None:
        # Minimal required keys for UMI row sanity
        required = ["game", "song_id", "note_total_chart", "duration_ms"]
        for k in required:
            if k not in canonical_row:
                errors.append(f"Missing required field '{k}' in canonical_row.")
        if errors:
            return

        if canonical_row.get("game") != "arcaea":
            errors.append(f"canonical_row['game'] must be 'arcaea', got {canonical_row.get('game')!r}.")

        ntc = canonical_row.get("note_total_chart")
        if not isinstance(ntc, int) or ntc <= 0:
            errors.append(f"canonical_row['note_total_chart'] must be a positive int, got {ntc!r}.")

        dur = canonical_row.get("duration_ms")
        if not isinstance(dur, int) or dur <= 0:
            errors.append(f"canonical_row['duration_ms'] must be a positive int, got {dur!r}.")

    @staticmethod
    def _run_report(report: Any, *, label: str) -> Dict[str, Any]:
        """
        Normalize different report dict shapes into:
          { ok: bool, errors: list[str] }
        """
        if not isinstance(report, dict):
            return {"ok": False, "errors": [f"{label}: report is not a dict ({type(report).__name__})."]}

        ok = bool(report.get("ok"))
        errs = report.get("errors") or []
        if not isinstance(errs, list):
            errs = [f"{label}: report.errors is not a list ({type(errs).__name__})."]
            ok = False

        # Ensure all errors are strings
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

        Supports either:
        - sections[*]['end_ms'] if present
        - otherwise returns [] (skip section validation)

        This is non-invasive and only activates when ms fields exist.
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

        # must be sorted ascending, unique
        boundaries = sorted(set(boundaries))
        return boundaries


__all__ = ["ArcaeaValidator"]
