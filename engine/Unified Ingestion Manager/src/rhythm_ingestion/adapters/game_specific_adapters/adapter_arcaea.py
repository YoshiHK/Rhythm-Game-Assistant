#!/usr/bin/env python3
from __future__ import annotations

"""
adapter_arcaea.py (FULL REPLACEMENT - v2 normalized)

UMI Phase 3 adapter for Arcaea.

Responsibilities:
- load AFF chart -> Chart
- normalize Chart -> canonical payload
- preserve raw timing / geometry in extra
- build conservative sections from chart timing windows
- guarantee minimal payload contract through BaseAdapterV2

Design notes:
- additive only
- do not rewrite completed Arcaea gameplay logic
- no validator imports
- no persistence
- no verification
- no gameplay inference beyond structural normalization
"""

# ---------------------------------------------------------------------
# Standard library imports
# ---------------------------------------------------------------------
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

# ---------------------------------------------------------------------
# Base adapter + shared adapter utilities
# ---------------------------------------------------------------------
from ..base_adapter_v2 import BaseAdapterV2
from ..common_adapter_utils import (
    build_internal_metadata,
    canonical_sections_version,
    attach_if_missing,
)

# ---------------------------------------------------------------------
# Local parser / model imports
# ---------------------------------------------------------------------
from .aff.decoder import parse_aff
from .utils import read_file
from .arcaea_element import Chart, Tap, Hold, Arc, ArcTap, Flick

try:
    from .arcaea_element import Timing  # type: ignore
except Exception:
    Timing = Any  # type: ignore

try:
    from .sample import Sample  # type: ignore
except Exception:
    try:
        from .arcaea_element import Sample  # type: ignore
    except Exception:
        Sample = None  # type: ignore


# ---------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------
GAME_ID = "arcaea"
SECTION_VERSION = canonical_sections_version(GAME_ID, "adapter_arcaea", "v2")

_CANONICAL_KINDS = {
    "tap",
    "critical_tap",
    "flick_arrow",
    "hold_body_or_start",
    "hold_path",
}

_ALLOWED_EXTS = {".aff"}

# Combo-bearing raw types (used for row fallback and diagnostics)
_COMBO_RAW_TYPES = {
    "tap",
    "arctap",
    "flick",
    "hold_start",
    "hold_end",
}

# ---------------------------------------------------------------------
# Arcaea note type mapping
# ---------------------------------------------------------------------
class ArcaeaNoteEventType:
    TAP = "tap"
    HOLD_START = "hold_start"
    HOLD_END = "hold_end"
    HOLD_BODY = "hold_body"
    ARC_FLOOR = "arc_floor"
    ARC_SKY = "arc_sky"
    ARCTAP = "arctap"
    FLICK = "flick"


def map_arcaea_type_to_kind(raw_type: str) -> str:
    if raw_type == ArcaeaNoteEventType.TAP:
        return "tap"
    if raw_type == ArcaeaNoteEventType.ARCTAP:
        return "flick_arrow"
    if raw_type == ArcaeaNoteEventType.FLICK:
        return "flick_arrow"
    if raw_type in {ArcaeaNoteEventType.HOLD_START, ArcaeaNoteEventType.HOLD_END}:
        return "hold_body_or_start"
    if raw_type in {ArcaeaNoteEventType.HOLD_BODY, ArcaeaNoteEventType.ARC_FLOOR, ArcaeaNoteEventType.ARC_SKY}:
        return "hold_path"
    return "tap"


# ---------------------------------------------------------------------
# arcsong.json lookup (lazy, fallback-safe)
# ---------------------------------------------------------------------
def _load_arcsong_db() -> List[Dict[str, Any]]:
    """
    Best-effort loader for arcsong.json.

    Returns [] if not found / unreadable.
    """
    candidates = [
        Path(__file__).with_name("arcsong.json"),
        Path(__file__).resolve().parent / "arcsong.json",
        Path.cwd() / "arcsong.json",
    ]

    for p in candidates:
        try:
            if p.exists():
                raw = json.loads(p.read_text(encoding="utf-8"))
                if isinstance(raw, list):
                    return raw
        except Exception:
            continue
    return []


_ARCSONG_DB = _load_arcsong_db()


# ---------------------------------------------------------------------
# Raw loading
# ---------------------------------------------------------------------
def load_chart(source_ref: Union[str, Chart]) -> Chart:
    """
    Load an Arcaea chart from .aff path or pass through an existing Chart.
    """
    if isinstance(source_ref, Chart):
        return source_ref

    aff_text = read_file(source_ref)
    chart: Chart = parse_aff(aff_text)
    return chart


# ---------------------------------------------------------------------
# Timing helpers
# ---------------------------------------------------------------------
def _ms_to_beats(chart: Chart, t_ms: int) -> float:
    """
    Convert an absolute time in ms to beats using chart timing data.
    """
    positions = getattr(chart, "timing_position_list", []) or []
    bpms = getattr(chart, "timing_value_list", []) or []
    beats_offsets = getattr(chart, "timing_beats_list", []) or []

    if not bpms or not positions or not beats_offsets:
        return 0.0

    if t_ms <= positions[0]:
        bpm0 = bpms[0]
        return beats_offsets[0] + (t_ms - positions[0]) * bpm0 / 60000.0

    last_index = len(bpms) - 1

    for i in range(last_index):
        t0 = positions[i]
        t1 = positions[i + 1]
        if t0 <= t_ms < t1:
            bpm = bpms[i]
            return beats_offsets[i] + (t_ms - t0) * bpm / 60000.0

    t0 = positions[last_index]
    bpm = bpms[last_index]
    return beats_offsets[last_index] + (t_ms - t0) * bpm / 60000.0


def _lane_from_ground_lane(lane_value: float) -> int:
    """
    Map Arcaea ground lane to canonical lane index.
    """
    return int(round(lane_value))


def _build_chart_meta(chart: Chart) -> Dict[str, Any]:
    """
    Build chart_meta from Chart timing info.
    """
    if getattr(chart, "sorted_timing_list", None):
        base_timing = chart.sorted_timing_list[0]
        base_bpm = getattr(base_timing, "bpm", 0.0)
    else:
        base_bpm = 0.0

    start_ms, end_ms = chart.get_interval()
    max_time_beats = _ms_to_beats(chart, end_ms)

    return {
        "bpm": float(base_bpm or 0.0),
        "max_time_beats": float(max_time_beats),
    }


# ---------------------------------------------------------------------
# Note normalization
# ---------------------------------------------------------------------
def normalize_events(raw_chart: Chart) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Normalize an Arcaea Chart into chart_meta and canonical note_events.
    """
    chart: Chart = raw_chart

    chart_meta = _build_chart_meta(chart)
    note_events: List[Dict[str, Any]] = []

    # --- Taps (ground) ---
    for tap in chart.get_command_list_for_type(Tap, search_in_timing_group=True, exclude_noinput=False):
        raw_type = ArcaeaNoteEventType.TAP
        note_events.append({
            "time_beats": _ms_to_beats(chart, tap.t),
            "lane": _lane_from_ground_lane(tap.lane),
            "kind": map_arcaea_type_to_kind(raw_type),
            "extra": {
                "raw_type": raw_type,
                "time_ms": tap.t,
                "width_lanes": 1,
            },
        })

    # --- Holds (ground) ---
    for hold in chart.get_command_list_for_type(Hold, search_in_timing_group=True, exclude_noinput=False):
        if hold.t1 == hold.t2:
            continue

        start_beats = _ms_to_beats(chart, hold.t1)
        end_beats = _ms_to_beats(chart, hold.t2)
        lane = _lane_from_ground_lane(hold.lane)

        # Start
        note_events.append({
            "time_beats": start_beats,
            "lane": lane,
            "kind": map_arcaea_type_to_kind(ArcaeaNoteEventType.HOLD_START),
            "extra": {
                "raw_type": ArcaeaNoteEventType.HOLD_START,
                "time_ms": hold.t1,
                "width_lanes": 1,
                "rect_height": end_beats - start_beats,
            },
        })

        # End
        note_events.append({
            "time_beats": end_beats,
            "lane": lane,
            "kind": map_arcaea_type_to_kind(ArcaeaNoteEventType.HOLD_END),
            "extra": {
                "raw_type": ArcaeaNoteEventType.HOLD_END,
                "time_ms": hold.t2,
                "width_lanes": 1,
            },
        })

        # Body
        note_events.append({
            "time_beats": start_beats,
            "lane": lane,
            "kind": map_arcaea_type_to_kind(ArcaeaNoteEventType.HOLD_BODY),
            "extra": {
                "raw_type": ArcaeaNoteEventType.HOLD_BODY,
                "time_ms": hold.t1,
                "width_lanes": 1,
                "rect_height": end_beats - start_beats,
                "shape": "hold",
            },
        })

    # --- Arcs (sampled if possible, otherwise conservative fallback) ---
    for arc in chart.get_command_list_for_type(Arc, search_in_timing_group=True, exclude_noinput=False):
        raw_type = ArcaeaNoteEventType.ARC_SKY if getattr(arc, "is_skyline", False) else ArcaeaNoteEventType.ARC_FLOOR
        kind = map_arcaea_type_to_kind(raw_type)

        if Sample is not None:
            try:
                sample = Sample(arc)
                for _x_pixel, t_ms, alpha in sample.get_coordinate_list(sampling_rate=10):
                    x_norm, z_norm = sample.get_coordinate_tuple(t_ms)
                    note_events.append({
                        "time_beats": _ms_to_beats(chart, t_ms),
                        "lane": 0,
                        "kind": kind,
                        "extra": {
                            "raw_type": raw_type,
                            "time_ms": t_ms,
                            "width_lanes": 1,
                            "shape": "arc",
                            "arc_x_norm": x_norm,
                            "arc_z_norm": z_norm,
                            "alpha": alpha,
                        },
                    })
            except Exception:
                # conservative fallback to start anchor
                note_events.append({
                    "time_beats": _ms_to_beats(chart, arc.t1),
                    "lane": 0,
                    "kind": kind,
                    "extra": {
                        "raw_type": raw_type,
                        "time_ms": arc.t1,
                        "width_lanes": 1,
                        "shape": "arc",
                    },
                })
        else:
            note_events.append({
                "time_beats": _ms_to_beats(chart, arc.t1),
                "lane": 0,
                "kind": kind,
                "extra": {
                    "raw_type": raw_type,
                    "time_ms": arc.t1,
                    "width_lanes": 1,
                    "shape": "arc",
                },
            })

    # --- ArcTaps ---
    for arc in chart.get_command_list_for_type(Arc, search_in_timing_group=True, exclude_noinput=False):
        if not getattr(arc, "arctap_list", None):
            continue

        if Sample is not None:
            try:
                sample = Sample(arc)
            except Exception:
                sample = None
        else:
            sample = None

        for arctap in arc.arctap_list:
            extra: Dict[str, Any] = {
                "raw_type": ArcaeaNoteEventType.ARCTAP,
                "time_ms": arctap.tn,
                "width_lanes": 1,
                "shape": "arc",
                "direction": "up",
            }

            if sample is not None:
                try:
                    x_norm, z_norm = sample.get_coordinate_tuple(arctap.tn)
                    extra["arc_x_norm"] = x_norm
                    extra["arc_z_norm"] = z_norm
                except Exception:
                    pass

            note_events.append({
                "time_beats": _ms_to_beats(chart, arctap.tn),
                "lane": 0,
                "kind": map_arcaea_type_to_kind(ArcaeaNoteEventType.ARCTAP),
                "extra": extra,
            })

    # --- Free Flicks ---
    for flick in chart.get_command_list_for_type(Flick, search_in_timing_group=True, exclude_noinput=False):
        note_events.append({
            "time_beats": _ms_to_beats(chart, flick.t),
            "lane": 0,
            "kind": map_arcaea_type_to_kind(ArcaeaNoteEventType.FLICK),
            "extra": {
                "raw_type": ArcaeaNoteEventType.FLICK,
                "time_ms": flick.t,
                "width_lanes": 1,
                "shape": "free_flick",
                "x": getattr(flick, "x", None),
                "y": getattr(flick, "y", None),
                "vx": getattr(flick, "vx", None),
                "vy": getattr(flick, "vy", None),
            },
        })

    # Stable sort
    note_events.sort(
        key=lambda ev: (
            float(ev.get("time_beats", 0.0)),
            int(ev.get("lane", 0)),
            str(ev.get("kind", "")),
        )
    )

    return chart_meta, note_events


# ---------------------------------------------------------------------
# Validation / diagnostics helpers
# ---------------------------------------------------------------------
def validate_note_events(chart: Chart, note_events: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Validate canonical note_events against the original Arcaea Chart.

    This is adapter-local diagnostics only (not validator logic).
    """
    report: Dict[str, Any] = {
        "expected": {},
        "actual": {},
        "derived": {},
        "ok": True,
        "errors": [],
    }

    expected_tap = chart.get_combo_of(Tap)
    expected_arctap = chart.get_combo_of(ArcTap)
    expected_flick = chart.get_combo_of(Flick)

    expected_single_combo = expected_tap + expected_arctap + expected_flick

    expected_hold_long_combo = chart.get_long_note_combo(chart.get_command_list_for_type(Hold))
    expected_arc_long_combo = chart.get_long_note_combo(chart._connected_arc_list)
    expected_long_combo_total = expected_hold_long_combo + expected_arc_long_combo

    expected_total_combo = chart.get_total_combo()
    derived_total_combo_from_parts = expected_single_combo + expected_long_combo_total

    expected_hold_objects = len(list(chart.get_command_list_for_type(Hold)))
    expected_arc_objects = len(list(chart.get_command_list_for_type(Arc)))

    report["expected"] = {
        "tap_combo": expected_tap,
        "arctap_combo": expected_arctap,
        "flick_combo": expected_flick,
        "single_combo": expected_single_combo,
        "hold_long_combo": expected_hold_long_combo,
        "arc_long_combo": expected_arc_long_combo,
        "long_combo_total": expected_long_combo_total,
        "total_combo": expected_total_combo,
        "hold_objects": expected_hold_objects,
        "arc_objects": expected_arc_objects,
    }

    report["derived"] = {
        "total_combo_from_parts": derived_total_combo_from_parts,
    }

    if derived_total_combo_from_parts != expected_total_combo:
        report["ok"] = False
        report["errors"].append(
            f"Total combo mismatch inside Chart: get_total_combo()={expected_total_combo}, "
            f"but single_combo + long_combo_total={derived_total_combo_from_parts}."
        )

    actual_tap = 0
    actual_arctap = 0
    actual_flick = 0
    hold_start_events = 0
    arc_events = 0

    for ev in note_events:
        extra = ev.get("extra", {})
        raw_type = extra.get("raw_type")

        if raw_type == ArcaeaNoteEventType.TAP:
            actual_tap += 1
        elif raw_type == ArcaeaNoteEventType.ARCTAP:
            actual_arctap += 1
        elif raw_type == ArcaeaNoteEventType.FLICK:
            actual_flick += 1
        elif raw_type == ArcaeaNoteEventType.HOLD_START:
            hold_start_events += 1
        elif raw_type in {ArcaeaNoteEventType.ARC_FLOOR, ArcaeaNoteEventType.ARC_SKY}:
            arc_events += 1

    report["actual"] = {
        "tap_events": actual_tap,
        "arctap_events": actual_arctap,
        "flick_events": actual_flick,
        "hold_start_events": hold_start_events,
        "arc_events": arc_events,
    }

    if actual_tap != expected_tap:
        report["ok"] = False
        report["errors"].append(
            f"Tap mismatch: expected combo {expected_tap}, got {actual_tap} note_events"
        )

    if actual_arctap != expected_arctap:
        report["ok"] = False
        report["errors"].append(
            f"ArcTap mismatch: expected combo {expected_arctap}, got {actual_arctap} note_events"
        )

    if actual_flick != expected_flick:
        report["ok"] = False
        report["errors"].append(
            f"Flick mismatch: expected combo {expected_flick}, got {actual_flick} note_events"
        )

    if hold_start_events != expected_hold_objects:
        report["ok"] = False
        report["errors"].append(
            f"Hold start mismatch: expected {expected_hold_objects} Hold objects, got {hold_start_events} HOLD_START note_events"
        )

    if arc_events < expected_arc_objects:
        report["ok"] = False
        report["errors"].append(
            f"Arc events mismatch: expected at least {expected_arc_objects} Arc objects, but only found {arc_events} ARC_* note_events."
        )

    return report


def build_sections_from_boundaries(
    chart: Chart,
    note_events: List[Dict[str, Any]],
    section_boundaries_ms: List[int],
) -> List[Dict[str, Any]]:
    """
    Build conservative sections aligned with chart combo windows.
    """
    start_ms = 0
    end_chart_ms = chart.get_interval()[1]
    boundaries = [b for b in sorted(section_boundaries_ms) if 0 < b < end_chart_ms]
    boundaries.append(end_chart_ms)

    sections: List[Dict[str, Any]] = []
    prev_combo_prefix = chart.get_total_combo_before(start_ms)

    for end_ms in boundaries:
        combo_prefix_end = chart.get_total_combo_before(end_ms)
        expected_combo = combo_prefix_end - prev_combo_prefix

        section_events = [
            ev for ev in note_events
            if start_ms <= ev.get("extra", {}).get("time_ms", -1) < end_ms
        ]

        single_raw_types = {
            ArcaeaNoteEventType.TAP,
            ArcaeaNoteEventType.ARCTAP,
            ArcaeaNoteEventType.FLICK,
        }
        actual_single_events = sum(
            1 for ev in section_events
            if ev.get("extra", {}).get("raw_type") in single_raw_types
        )

        hold_start_events = sum(
            1 for ev in section_events
            if ev.get("extra", {}).get("raw_type") == ArcaeaNoteEventType.HOLD_START
        )
        arc_events = sum(
            1 for ev in section_events
            if ev.get("extra", {}).get("raw_type") in {
                ArcaeaNoteEventType.ARC_FLOOR,
                ArcaeaNoteEventType.ARC_SKY,
            }
        )

        start_beats = _ms_to_beats(chart, start_ms)
        end_beats = _ms_to_beats(chart, end_ms)

        duration_s = max(0.001, (end_ms - start_ms) / 1000.0)
        duration_beats = max(0.001, end_beats - start_beats)

        density_nps = len(section_events) / duration_s
        density_npb = len(section_events) / duration_beats

        sections.append({
            "start_ms": start_ms,
            "end_ms": end_ms,
            "start_beats": start_beats,
            "end_beats": end_beats,
            "expected_total_combo": expected_combo,
            "actual_single_events": actual_single_events,
            "actual_long_structural": {
                "hold_start_events": hold_start_events,
                "arc_events": arc_events,
            },
            "density_nps": density_nps,
            "density_npb": density_npb,
            "nps": density_nps,
            "npb": density_npb,
            "meta": {},
        })

        start_ms = end_ms
        prev_combo_prefix = combo_prefix_end

    return sections


# ---------------------------------------------------------------------
# Difficulty lookup
# ---------------------------------------------------------------------
def _infer_song_id_from_path(path: str) -> str:
    base = os.path.basename(path)
    name, _ = os.path.splitext(base)
    return name.split("_")[0]


def _map_arcaea_diff_code(num: int) -> str:
    if num >= 20:
        return "BYD"
    elif num >= 16:
        return "FTR"
    elif num >= 12:
        return "PRS"
    else:
        return "PST"


def _lookup_chart_difficulty_details(song_id: str, chart: Chart) -> Dict[str, Any] | None:
    total_combo = chart.get_total_combo()

    for s in _ARCSONG_DB:
        if s.get("song_id") == song_id:
            best = None
            best_delta = 1_000_000

            for diff in s.get("difficulties", []):
                diff_note = diff.get("note")
                if diff_note is None:
                    continue

                delta = abs(diff_note - total_combo)
                if delta < best_delta:
                    best_delta = delta
                    best = diff

            if best is None:
                return None

            diff_code = best.get("difficulty")
            rating_raw = best.get("rating")
            note = best.get("note")
            name_en = best.get("name_en")

            if rating_raw is None or diff_code is None or note is None:
                return None

            level = rating_raw // 5
            tier = _map_arcaea_diff_code(diff_code)
            label = f"{tier} {level}"

            note_delta = abs(total_combo - note)
            is_consistent = note_delta <= 10

            return {
                "song_id": song_id,
                "name_en": name_en,
                "difficulty_code": diff_code,
                "rating_raw": rating_raw,
                "level": level,
                "note": note,
                "tier": tier,
                "label": label,
                "note_delta": note_delta,
                "is_consistent": is_consistent,
            }

    return None


# ---------------------------------------------------------------------
# Module-level payload builder
# ---------------------------------------------------------------------
def build_canonical_payload_arcaea(source_ref: str) -> Dict[str, Any]:
    """
    Main entrypoint: convert an Arcaea chart into canonical payload.
    """
    chart = load_chart(source_ref)

    chart_meta, note_events = normalize_events(chart)

    song_id = _infer_song_id_from_path(source_ref)
    diff_info = _lookup_chart_difficulty_details(song_id, chart)
    difficulty_label = diff_info["label"] if diff_info is not None else "FTR"

    # Default 8 sections
    start_ms, end_ms = chart.get_interval()
    duration = end_ms - start_ms
    default_section_count = 8
    if duration <= 0 or default_section_count <= 0:
        section_boundaries_ms: List[int] = []
    else:
        step = duration // default_section_count
        section_boundaries_ms = [
            start_ms + step * i for i in range(1, default_section_count)
        ]

    sections = build_sections_from_boundaries(
        chart,
        note_events,
        section_boundaries_ms,
    )

    validation_report = validate_note_events(chart, note_events)

    adapter_metadata: Dict[str, Any] = {
        "adapter_id": "adapter_arcaea",
        "adapter_version": "2.0.0",
        "source_format": "aff",
        "source_path": source_ref,
        "notes": "Arcaea adapter using AFF + canonical note event normalization.",
        "song_id": song_id,
    }

    if diff_info is not None:
        adapter_metadata["difficulty_details"] = {
            "song_id": diff_info["song_id"],
            "name_en": diff_info["name_en"],
            "difficulty_code": diff_info["difficulty_code"],
            "rating_raw": diff_info["rating_raw"],
            "level": diff_info["level"],
            "note_total_db": diff_info["note"],
            "tier": diff_info["tier"],
        }
        adapter_metadata["difficulty_consistency"] = {
            "note_delta": diff_info["note_delta"],
            "is_consistent": diff_info["is_consistent"],
            "note_delta_threshold": 10,
            "chart_total_combo": chart.get_total_combo(),
        }
    else:
        adapter_metadata["difficulty_consistency"] = {
            "note_delta": None,
            "is_consistent": False,
            "note_delta_threshold": 10,
            "chart_total_combo": chart.get_total_combo(),
        }

    diagnostics: Dict[str, Any] = {
        "note_event_count": len(note_events),
        "sections_count": len(sections),
        "validation_report": validation_report,
    }

    if sections:
        diagnostics["avg_nps"] = sum(s.get("nps", 0.0) for s in sections) / max(1, len(sections))
        diagnostics["avg_npb"] = sum(s.get("npb", 0.0) for s in sections) / max(1, len(sections))

    internal_metadata = build_internal_metadata(
        adapter_id="adapter_arcaea",
        adapter_version="2.0.0",
        sections_source="adapter_arcaea.build_sections_from_boundaries",
    )

    payload: Dict[str, Any] = {
        "game_id": GAME_ID,
        "chart_id": str(Path(source_ref).resolve()),
        "title": diff_info["name_en"] if diff_info and diff_info.get("name_en") else song_id,
        "difficulty": difficulty_label,
        "note_events": note_events,
        "chart_meta": chart_meta,
        "adapter_metadata": adapter_metadata,
        "diagnostics": diagnostics,
        "internal_metadata": internal_metadata,
        "sections": sections,
        "canonical_sections_version": SECTION_VERSION,
    }

    return payload


# ---------------------------------------------------------------------
# Adapter class
# ---------------------------------------------------------------------
class ArcaeaAdapter(BaseAdapterV2):
    game_id = GAME_ID
    adapter_id = "adapter_arcaea"
    adapter_version = "2.0.0"

    def accepts_file(self, path) -> bool:
        p = Path(path)
        return p.suffix.lower() in _ALLOWED_EXTS

    def load(self, path):
        """
        Keep load() simple and stable.
        """
        return load_chart(path)

    def to_canonical_payload(self, source_ref: str) -> Dict[str, Any]:
        payload = build_canonical_payload_arcaea(source_ref)

        p = Path(source_ref)
        payload = self.finalize_payload_v2(
            payload,
            source_path=str(p),
            default_chart_id=payload.get("chart_id") or str(p.resolve()),
            default_difficulty=payload.get("difficulty") or "FTR",
        )

        return payload

    def to_canonical_row(self, raw: Any) -> Dict[str, Any]:
        if isinstance(raw, dict):
            payload = raw
        else:
            payload = self.to_canonical_payload(str(raw))

        note_events = payload.get("note_events") if isinstance(payload, dict) else []
        if not isinstance(note_events, list):
            note_events = []

        chart_meta = payload.get("chart_meta") if isinstance(payload, dict) else {}
        if not isinstance(chart_meta, dict):
            chart_meta = {}

        adapter_metadata = payload.get("adapter_metadata") if isinstance(payload, dict) else {}
        if not isinstance(adapter_metadata, dict):
            adapter_metadata = {}

        difficulty_details = adapter_metadata.get("difficulty_details")
        if not isinstance(difficulty_details, dict):
            difficulty_details = {}

        consistency = adapter_metadata.get("difficulty_consistency")
        if not isinstance(consistency, dict):
            consistency = {}

        bpm = chart_meta.get("bpm")
        max_time_beats = chart_meta.get("max_time_beats") or 0.0

        duration_ms = 0
        try:
            bpm_f = float(bpm)
            mtb_f = float(max_time_beats)
            if bpm_f > 0:
                duration_ms = int((mtb_f / bpm_f) * 60_000.0)
        except Exception:
            duration_ms = 0

        title = payload.get("title") or difficulty_details.get("name_en") or payload.get("chart_id")
        song_id = difficulty_details.get("song_id") or payload.get("chart_id")
        difficulty_label = payload.get("difficulty") or difficulty_details.get("tier") or "FTR"

        note_total_chart = consistency.get("chart_total_combo")
        if not isinstance(note_total_chart, int):
            note_total_chart = len([ev for ev in note_events if isinstance(ev, dict) and ev.get("extra", {}).get("raw_type") in _COMBO_RAW_TYPES])

        return {
            "game": GAME_ID,
            "game_id": GAME_ID,
            "song_id": song_id,
            "name": title,
            "title": title,
            "tier": difficulty_details.get("tier"),
            "level": difficulty_details.get("level"),
            "difficulty_code": difficulty_details.get("difficulty_code"),
            "difficulty_label": difficulty_label,
            "note_total_chart": int(note_total_chart),
            "note_total_db": difficulty_details.get("note_total_db"),
            "note_delta": consistency.get("note_delta"),
            "duration_ms": duration_ms,
            "bpm": bpm,
            "rating_raw": difficulty_details.get("rating_raw"),
            "chart_path": payload.get("chart_id"),
        }

    def capabilities(self) -> dict:
        return {
            "note_model": "hybrid_ground_arc",
            "supports_sections": True,
            "supports_variable_bpm": True,
            "supports_aff": True,
            "supports_arc_sampling": Sample is not None,
            "supports_db_lookup": bool(_ARCSONG_DB),
        }


__all__ = [
    "ArcaeaAdapter",
    "build_canonical_payload_arcaea",
    "load_chart",
]