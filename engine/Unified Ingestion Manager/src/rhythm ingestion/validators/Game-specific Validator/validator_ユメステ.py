#!/usr/bin/env python3
"""validator_ユメステ.py
UMI Phase 3 validator for ユメステ (夢のステラリウム / World Dai Star).

Single source of truth for ユメステ validation (Phase 3).

Enforces schema consistency checks (ユメステ.json):
- Y1 (error): All emitted note kinds must be within schema.notes.canonical_kinds.
- Y2 (error): Notes must map to valid stage lanes with monotonic timing.

Additional hard guard:
- Naming consistency: game_id must be the Japanese string "ユメステ" (row + payload + class).

Constraints:
- Phase-3 wiring only: NO mutation, NO enrichment.

I/O:
- Accepts either:
  (A) canonical_row: dict with key "canonical_payload" (dict), OR
  (B) canonical_payload: dict directly
- Returns a ValidationResult dict:
  { ok: bool, game_id: str, errors: [...], warnings: [...], diagnostics: {...} }

Y2 lane auto-detection precedence (highest -> lowest):
1) chart_meta.lane_min + chart_meta.lane_max
2) chart_meta.lane_count (aliases: num_lanes, stage_lanes, lane_total)
3) chart_meta.lanes (list length)
4) inferred from note_events
5) defaults

The validator exposes diagnostics.lane_bounds_source for precedence tests.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

# Support both package and script execution.
try:
    from .base_validator import BaseValidator
except Exception:  # pragma: no cover
    from base_validator import BaseValidator  # type: ignore


GAME_ID = "ユメステ"
CANONICAL_KINDS = {"tap", "hold_path", "slide", "flick"}

# Soft numeric tolerance for monotonic checks (beats)
_EPS = 1e-9

# Fallback lane bounds when chart_meta does not specify and we cannot infer.
DEFAULT_LANE_MIN = 0
DEFAULT_LANE_MAX = 7

# Safety cap: if inferred span is absurdly wide, warn + fallback.
_MAX_REASONABLE_LANE_SPAN = 32


def _is_number(x: Any) -> bool:
    # NaN guard: NaN != NaN
    return isinstance(x, (int, float)) and x == x


def _coerce_float(x: Any, default: Optional[float] = None) -> Optional[float]:
    try:
        if x is None or isinstance(x, bool):
            return default
        return float(x)
    except Exception:
        return default


def _coerce_int(x: Any, default: Optional[int] = None) -> Optional[int]:
    try:
        if x is None or isinstance(x, bool):
            return default
        return int(x)
    except Exception:
        return default


def _get_payload(row_or_payload: Dict[str, Any]) -> Tuple[Dict[str, Any], bool]:
    """Return (payload, is_row)."""
    if isinstance(row_or_payload.get("canonical_payload"), dict):
        return row_or_payload["canonical_payload"], True
    return row_or_payload, False


def _lane_bounds_from_chart_meta(
    chart_meta: Dict[str, Any],
    note_events: List[Dict[str, Any]],
) -> Tuple[int, int, str, List[Dict[str, Any]]]:
    """Determine lane bounds (min,max) with source label and warnings."""
    warns: List[Dict[str, Any]] = []

    # 1) explicit min/max
    lm = _coerce_int(chart_meta.get("lane_min"), None)
    lx = _coerce_int(chart_meta.get("lane_max"), None)
    if lm is not None and lx is not None and lm <= lx:
        return lm, lx, "chart_meta.lane_min/lane_max", warns

    # 2) lane_count aliases
    for k in ("lane_count", "num_lanes", "stage_lanes", "lane_total"):
        c = _coerce_int(chart_meta.get(k), None)
        if c is not None and c > 0:
            return 0, c - 1, f"chart_meta.{k}", warns

    # 3) lanes list
    lanes = chart_meta.get("lanes")
    if isinstance(lanes, (list, tuple)) and len(lanes) > 0:
        return 0, len(lanes) - 1, "chart_meta.lanes", warns

    # 4) infer from note_events
    observed: List[int] = []
    for ev in note_events:
        if not isinstance(ev, dict):
            continue
        li = _coerce_int(ev.get("lane"), None)
        if li is not None:
            observed.append(li)

    if observed:
        mn, mx = min(observed), max(observed)
        if mx - mn > _MAX_REASONABLE_LANE_SPAN:
            warns.append({
                "code": "Y2_LANE_BOUNDS_SUSPECT",
                "message": (
                    f"Inferred lane span too large ({mn}..{mx}); falling back to defaults "
                    f"{DEFAULT_LANE_MIN}..{DEFAULT_LANE_MAX}."
                ),
            })
            return DEFAULT_LANE_MIN, DEFAULT_LANE_MAX, "default", warns
        return mn, mx, "inferred(note_events)", warns

    # 5) defaults
    return DEFAULT_LANE_MIN, DEFAULT_LANE_MAX, "default", warns


def _is_valid_lane(lane: Optional[int], lane_min: int, lane_max: int) -> bool:
    return lane is not None and lane_min <= lane <= lane_max


class ユメステValidator(BaseValidator):
    """Validator for ユメステ canonical payloads."""

    game_id = GAME_ID

    def validate(self, row_or_payload: Dict[str, Any]) -> Dict[str, Any]:
        errors: List[Dict[str, Any]] = []
        warnings: List[Dict[str, Any]] = []
        diagnostics: Dict[str, Any] = {}

        if not isinstance(row_or_payload, dict):
            return {
                "ok": False,
                "game_id": GAME_ID,
                "errors": [{"code": "Y0", "message": "Input must be a dict (canonical_row or canonical_payload)."}],
                "warnings": [],
                "diagnostics": {},
            }

        payload, is_row = _get_payload(row_or_payload)

        # Naming consistency
        row_game = row_or_payload.get("game_id") if is_row else None
        payload_game = payload.get("game_id")
        if row_game is not None and row_game != GAME_ID:
            errors.append({"code": "Y_NAME_ROW", "message": f"Row game_id must be '{GAME_ID}' but got '{row_game}'."})
        if payload_game is not None and payload_game != GAME_ID:
            errors.append({"code": "Y_NAME_PAYLOAD", "message": f"Payload game_id must be '{GAME_ID}' but got '{payload_game}'."})

        # note_events
        note_events = payload.get("note_events")
        if not isinstance(note_events, list):
            errors.append({"code": "Y_NOTE_EVENTS_MISSING", "message": "canonical_payload.note_events must be a list."})
            note_events = []

        ne_dicts: List[Dict[str, Any]] = [ev for ev in note_events if isinstance(ev, dict)]
        diagnostics["note_events_count"] = len(note_events)
        diagnostics["note_events_dict_count"] = len(ne_dicts)

        # chart_meta lane bounds
        chart_meta = payload.get("chart_meta")
        if not isinstance(chart_meta, dict):
            chart_meta = {}

        lane_min, lane_max, lane_src, lane_warns = _lane_bounds_from_chart_meta(chart_meta, ne_dicts)
        diagnostics["lane_min"] = lane_min
        diagnostics["lane_max"] = lane_max
        diagnostics["lane_bounds_source"] = lane_src
        warnings.extend(lane_warns)

        # Y1 kinds
        for i, ev in enumerate(note_events):
            if not isinstance(ev, dict):
                errors.append({"code": "Y1_EVENT_TYPE", "message": f"note_events[{i}] must be a dict."})
                continue
            kind = ev.get("kind")
            if kind is None:
                errors.append({"code": "Y1_KIND_MISSING", "message": f"note_events[{i}].kind is missing."})
                continue
            if kind not in CANONICAL_KINDS:
                errors.append({"code": "Y1_KIND_INVALID", "message": f"note_events[{i}].kind='{kind}' is not in allowed kinds {sorted(CANONICAL_KINDS)}."})

        # Y2 monotonic time + lane validity
        last_t: Optional[float] = None
        for i, ev in enumerate(note_events):
            if not isinstance(ev, dict):
                continue

            t = _coerce_float(ev.get("time_beats"), default=None)
            if t is None or not _is_number(t) or t < -_EPS:
                errors.append({"code": "Y2_TIME_INVALID", "message": f"note_events[{i}].time_beats must be a non-negative number."})
            else:
                if last_t is not None and t + _EPS < last_t:
                    errors.append({"code": "Y2_TIME_NONMONOTONIC", "message": f"note_events timing is not monotonic at index {i}: {t} < {last_t}."})
                last_t = t

            lane = _coerce_int(ev.get("lane"), default=None)
            if not _is_valid_lane(lane, lane_min, lane_max):
                errors.append({"code": "Y2_LANE_INVALID", "message": f"note_events[{i}].lane must be an integer in [{lane_min},{lane_max}] (source: {lane_src})."})

        return {
            "ok": len(errors) == 0,
            "game_id": GAME_ID,
            "errors": errors,
            "warnings": warnings,
            "diagnostics": diagnostics,
        }

    def validate_row(self, canonical_row: Dict[str, Any]) -> Dict[str, Any]:
        return self.validate(canonical_row)


def run_precedence_tests(verbose: bool = False) -> None:
    """Run precedence tests.

    Args:
        verbose: If True, prints PASS lines for every case in addition to failures.

    The runner always prints detailed failure logs.
    """

    v = ユメステValidator()
    failures: List[str] = []

    def has_code(res: Dict[str, Any], code: str) -> bool:
        return any(isinstance(e, dict) and e.get("code") == code for e in (res.get("errors") or []))

    def log_failure(name: str, res: Dict[str, Any], expect: Dict[str, Any]) -> None:
        print("\n[PRECEDENCE TEST FAILED]", name)
        print("  Expected:", expect)
        diag = res.get("diagnostics") or {}
        print("  Actual: ok=", res.get("ok"))
        print("         lane_bounds_source=", diag.get("lane_bounds_source"))
        print("         lane_min/max=", diag.get("lane_min"), "..", diag.get("lane_max"))
        print("  Errors:")
        for e in (res.get("errors") or []):
            print("   -", e)
        print("  Diagnostics:", diag)

    def log_pass(name: str, res: Dict[str, Any]) -> None:
        diag = res.get("diagnostics") or {}
        print("[PASS]", name, "| source=", diag.get("lane_bounds_source"), "| bounds=", diag.get("lane_min"), "..", diag.get("lane_max"), "| ok=", res.get("ok"))

    def check_case(name: str, row: Dict[str, Any], expect: Dict[str, Any]) -> None:
        res = v.validate_row(row)

        ok_exp = expect.get("ok")
        src_exp = expect.get("lane_bounds_source")
        mn_exp = expect.get("lane_min")
        mx_exp = expect.get("lane_max")
        must_code = expect.get("must_have_error_code")

        diag = res.get("diagnostics") or {}
        passed = True

        if ok_exp is not None and bool(res.get("ok")) != bool(ok_exp):
            passed = False
        if src_exp is not None and diag.get("lane_bounds_source") != src_exp:
            passed = False
        if mn_exp is not None and diag.get("lane_min") != mn_exp:
            passed = False
        if mx_exp is not None and diag.get("lane_max") != mx_exp:
            passed = False
        if must_code is not None and not has_code(res, must_code):
            passed = False

        if not passed:
            failures.append(name)
            log_failure(name, res, expect)
        elif verbose:
            log_pass(name, res)

    # ------------------------------------------------------------
    # Distinct fingerprints:
    # - lane_min/max: 10..10
    # - lane_count:   0..2   (lane_count=3)
    # - lanes(list):  0..8   (len=9)
    # - inferred:     21..23 (note_events only)
    # ------------------------------------------------------------

    infer_2_5 = [{"kind": "tap", "time_beats": 1.0, "lane": 2}, {"kind": "tap", "time_beats": 2.0, "lane": 5}]
    infer_8_9 = [{"kind": "tap", "time_beats": 1.0, "lane": 8}, {"kind": "tap", "time_beats": 2.0, "lane": 9}]
    infer_21_23 = [{"kind": "tap", "time_beats": 1.0, "lane": 21}, {"kind": "tap", "time_beats": 2.0, "lane": 23}]

    # Pairwise
    check_case(
        "P1 lane_min/max > inferred",
        {"game_id": GAME_ID, "canonical_payload": {"game_id": GAME_ID, "chart_meta": {"lane_min": 10, "lane_max": 10}, "note_events": infer_2_5}},
        {"ok": False, "must_have_error_code": "Y2_LANE_INVALID", "lane_bounds_source": "chart_meta.lane_min/lane_max", "lane_min": 10, "lane_max": 10},
    )

    check_case(
        "P2 lane_count > inferred",
        {"game_id": GAME_ID, "canonical_payload": {"game_id": GAME_ID, "chart_meta": {"lane_count": 3}, "note_events": infer_2_5}},
        {"ok": False, "must_have_error_code": "Y2_LANE_INVALID", "lane_bounds_source": "chart_meta.lane_count", "lane_min": 0, "lane_max": 2},
    )

    check_case(
        "P3 lanes(list) > inferred",
        {"game_id": GAME_ID, "canonical_payload": {"game_id": GAME_ID, "chart_meta": {"lanes": list(range(9))}, "note_events": infer_8_9}},
        {"ok": False, "must_have_error_code": "Y2_LANE_INVALID", "lane_bounds_source": "chart_meta.lanes", "lane_min": 0, "lane_max": 8},
    )

    check_case(
        "P4 inferred baseline",
        {"game_id": GAME_ID, "canonical_payload": {"game_id": GAME_ID, "note_events": infer_21_23}},
        {"ok": True, "lane_bounds_source": "inferred(note_events)", "lane_min": 21, "lane_max": 23},
    )

    # Triangular
    check_case(
        "T1 lane_min/max > lane_count > lanes",
        {"game_id": GAME_ID, "canonical_payload": {"game_id": GAME_ID, "chart_meta": {"lane_min": 10, "lane_max": 10, "lane_count": 3, "lanes": list(range(9))}, "note_events": infer_2_5}},
        {"ok": False, "must_have_error_code": "Y2_LANE_INVALID", "lane_bounds_source": "chart_meta.lane_min/lane_max", "lane_min": 10, "lane_max": 10},
    )

    check_case(
        "T2 lane_min/max > lane_count > inferred",
        {"game_id": GAME_ID, "canonical_payload": {"game_id": GAME_ID, "chart_meta": {"lane_min": 10, "lane_max": 10, "lane_count": 3}, "note_events": infer_2_5}},
        {"ok": False, "must_have_error_code": "Y2_LANE_INVALID", "lane_bounds_source": "chart_meta.lane_min/lane_max", "lane_min": 10, "lane_max": 10},
    )

    check_case(
        "T3 lane_min/max > lanes > inferred",
        {"game_id": GAME_ID, "canonical_payload": {"game_id": GAME_ID, "chart_meta": {"lane_min": 10, "lane_max": 10, "lanes": list(range(9))}, "note_events": infer_2_5}},
        {"ok": False, "must_have_error_code": "Y2_LANE_INVALID", "lane_bounds_source": "chart_meta.lane_min/lane_max", "lane_min": 10, "lane_max": 10},
    )

    check_case(
        "T4 lane_count > lanes > inferred",
        {"game_id": GAME_ID, "canonical_payload": {"game_id": GAME_ID, "chart_meta": {"lane_count": 3, "lanes": list(range(9))}, "note_events": infer_2_5}},
        {"ok": False, "must_have_error_code": "Y2_LANE_INVALID", "lane_bounds_source": "chart_meta.lane_count", "lane_min": 0, "lane_max": 2},
    )

    # Quadruple
    check_case(
        "Q lane_min/max wins when all present",
        {"game_id": GAME_ID, "canonical_payload": {"game_id": GAME_ID, "chart_meta": {"lane_min": 10, "lane_max": 10, "lane_count": 3, "lanes": list(range(9))}, "note_events": infer_2_5}},
        {"ok": False, "must_have_error_code": "Y2_LANE_INVALID", "lane_bounds_source": "chart_meta.lane_min/lane_max", "lane_min": 10, "lane_max": 10},
    )

    if failures:
        raise AssertionError(f"{len(failures)} precedence tests failed: {failures}")

    print("ユメステ precedence tests passed")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run ユメステ validator precedence tests")
    parser.add_argument("--verbose", action="store_true", help="Print PASS lines for each test case")
    args = parser.parse_args()
    run_precedence_tests(verbose=args.verbose)

