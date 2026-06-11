"""Reference adapter for Arcaea charts.

This module implements the Adapter SDK interface for Arcaea,
producing canonical chart payloads that validate against
`canonical_chart_payload.schema.json`.

NOTE: This is a skeleton and depends on an AFF parser providing
`Chart`, `Tap`, `Hold`, `Arc`, `ArcTap`, and `Flick` objects as
defined in `arcaea_element.py`.
"""
from typing import Any, Dict, List, Tuple
import json
import os

# Path to arcsong.json (Arcaea fan song DB)
_ARCSONG_PATH = os.path.join(os.path.dirname(__file__), "arcsong.json")

with open(_ARCSONG_PATH, "r", encoding="utf-8") as _f:
    _ARCSONG_DB = json.load(_f)["songs"]  # "songs": [...] [1](https://onedrive.live.com?cid=D5D62A1EF303BA22&id=D5D62A1EF303BA22!s0d6babc44a7a4ed698aad027e9f6d0f6)

# Types for clarity
RawChart = Any
ChartMeta = Dict[str, Any]
NoteEvent = Dict[str, Any]
CanonicalChartPayload = Dict[str, Any]

from .aff.decoder import parse_aff         # same as arcaea_render [1](https://onedrive.live.com?cid=D5D62A1EF303BA22&id=D5D62A1EF303BA22!s0d6babc44a7a4ed698aad027e9f6d0f6)
from .utils import read_file               # same helper used by the renderer [1](https://onedrive.live.com?cid=D5D62A1EF303BA22&id=D5D62A1EF303BA22!s0d6babc44a7a4ed698aad027e9f6d0f6)
from .arcaea_element import Chart          # ensure Chart is imported [2](https://onedrive.live.com?cid=D5D62A1EF303BA22&id=D5D62A1EF303BA22!sbd330b44279b4475b30768837728b1b3)

from typing import Union

def load_chart(source_ref: Union[str, Chart]) -> Chart:
    """
    Load an Arcaea chart from .aff path or pass through an existing Chart.
    """
    if isinstance(source_ref, Chart):
        return source_ref

    aff_text = read_file(source_ref)
    chart: Chart = parse_aff(aff_text)
    return chart

from typing import Any, Dict, List, Tuple

from .arcaea_element import Chart, Tap, Hold, Arc, ArcTap, Flick, Timing  # [1](https://onedrive.live.com?cid=D5D62A1EF303BA22&id=D5D62A1EF303BA22!s0d6babc44a7a4ed698aad027e9f6d0f6)
from .arcaea_note_event_type import ArcaeaNoteEventType, map_arcaea_type_to_kind  # 
from .arcaea_render import Sample  # for arc sampling [2](https://onedrive.live.com/personal/d5d62a1ef303ba22/_layouts/15/doc.aspx?resid=ee88c222-ce00-4968-8aad-d04f7ce2fa68&cid=d5d62a1ef303ba22)

def _ms_to_beats(chart: Chart, t_ms: int) -> float:
    """
    Convert an absolute time in ms to beats using the chart's Timing data.

    Uses Chart.timing_position_list, timing_value_list, timing_beats_list. [1](https://onedrive.live.com?cid=D5D62A1EF303BA22&id=D5D62A1EF303BA22!s0d6babc44a7a4ed698aad027e9f6d0f6)
    """
    positions = chart.timing_position_list        # [t0, t1, ..., t_n, end_time]
    bpms = chart.timing_value_list               # [bpm0, bpm1, ..., bpm_{n-1}]
    beats_offsets = chart.timing_beats_list      # [beats0, beats1, ..., beats_{n-1}]

    if not bpms:
        return 0.0

    # Before first timing point
    if t_ms <= positions[0]:
        bpm0 = bpms[0]
        return beats_offsets[0] + (t_ms - positions[0]) * bpm0 / 60000.0

    last_index = len(bpms) - 1

    # Within known timing intervals
    for i in range(last_index):
        t0 = positions[i]
        t1 = positions[i + 1]
        if t0 <= t_ms < t1:
            bpm = bpms[i]
            return beats_offsets[i] + (t_ms - t0) * bpm / 60000.0

    # After last timing point: extend last bpm
    t0 = positions[last_index]
    bpm = bpms[last_index]
    return beats_offsets[last_index] + (t_ms - t0) * bpm / 60000.0


def _lane_from_ground_lane(lane_value: float) -> int:
    """
    Map Arcaea's ground lane (Tap/Hold.lane) to canonical lane index.

    Renderer treats `lane` as discrete lane index (1..4). [2](https://onedrive.live.com/personal/d5d62a1ef303ba22/_layouts/15/doc.aspx?resid=ee88c222-ce00-4968-8aad-d04f7ce2fa68&cid=d5d62a1ef303ba22)
    """
    return int(round(lane_value))


def _build_chart_meta(chart: Chart) -> Dict[str, Any]:
    """Build chart_meta from Chart timing info. [1](https://onedrive.live.com?cid=D5D62A1EF303BA22&id=D5D62A1EF303BA22!s0d6babc44a7a4ed698aad027e9f6d0f6)"""
    if chart.sorted_timing_list:
        base_timing: Timing = chart.sorted_timing_list[0]
        base_bpm = base_timing.bpm
    else:
        base_bpm = 0.0

    start_ms, end_ms = chart.get_interval()
    max_time_beats = _ms_to_beats(chart, end_ms)

    return {
        "bpm": base_bpm,
        "max_time_beats": max_time_beats,
    }


def normalize_events(raw_chart: Chart) -> Tuple[ChartMeta, List[NoteEvent]]:
    """
    Normalize an Arcaea Chart into chart_meta and canonical note_events.

    Parameters
    ----------
    raw_chart : Chart
        Parsed Arcaea chart (AFF) as defined in `arcaea_element.py`. [1](https://onedrive.live.com?cid=D5D62A1EF303BA22&id=D5D62A1EF303BA22!s0d6babc44a7a4ed698aad027e9f6d0f6)
    """
    chart: Chart = raw_chart

    chart_meta: ChartMeta = _build_chart_meta(chart)
    note_events: List[NoteEvent] = []

    # --- Taps (ground) ---
    for tap in chart.get_command_list_for_type(Tap, search_in_timing_group=True, exclude_noinput=False):
        # Renderer uses tap.lane directly as lane index. [2](https://onedrive.live.com/personal/d5d62a1ef303ba22/_layouts/15/doc.aspx?resid=ee88c222-ce00-4968-8aad-d04f7ce2fa68&cid=d5d62a1ef303ba22)
        raw_type = ArcaeaNoteEventType.TAP
        kind = map_arcaea_type_to_kind(raw_type)
        note_events.append({
            "time_beats": _ms_to_beats(chart, tap.t),
            "lane": _lane_from_ground_lane(tap.lane),
            "kind": kind,
            "extra": {
                "raw_type": raw_type.value,
                "time_ms": tap.t,
                "width_lanes": 1,
            },
        })

    # --- Holds (ground) ---
    for hold in chart.get_command_list_for_type(Hold, search_in_timing_group=True, exclude_noinput=False):
        if hold.t1 == hold.t2:
            continue  # zero-length hold

        start_beats = _ms_to_beats(chart, hold.t1)
        end_beats = _ms_to_beats(chart, hold.t2)
        lane = _lane_from_ground_lane(hold.lane)

        # Start
        raw_type_start = ArcaeaNoteEventType.HOLD_START
        kind_start = map_arcaea_type_to_kind(raw_type_start)
        note_events.append({
            "time_beats": start_beats,
            "lane": lane,
            "kind": kind_start,
            "extra": {
                "raw_type": raw_type_start.value,
                "time_ms": hold.t1,
                "width_lanes": 1,
                "rect_height": end_beats - start_beats,
            },
        })

        # End
        raw_type_end = ArcaeaNoteEventType.HOLD_END
        kind_end = map_arcaea_type_to_kind(raw_type_end)
        note_events.append({
            "time_beats": end_beats,
            "lane": lane,
            "kind": kind_end,
            "extra": {
                "raw_type": raw_type_end.value,
                "time_ms": hold.t2,
                "width_lanes": 1,
            },
        })

        # Body as a single path segment
        raw_type_body = ArcaeaNoteEventType.HOLD_BODY
        kind_body = map_arcaea_type_to_kind(raw_type_body)
        note_events.append({
            "time_beats": start_beats,
            "lane": lane,
            "kind": kind_body,
            "extra": {
                "raw_type": raw_type_body.value,
                "time_ms": tap.t,
                "width_lanes": 1,
                "rect_height": end_beats - start_beats,
                "shape": "hold",
            },
        })

    # --- Arcs (floor & skyline) ---
    # We sample arcs using Sample(arc) exactly as renderer does. [2](https://onedrive.live.com/personal/d5d62a1ef303ba22/_layouts/15/doc.aspx?resid=ee88c222-ce00-4968-8aad-d04f7ce2fa68&cid=d5d62a1ef303ba22)
    for arc in chart.get_command_list_for_type(Arc, search_in_timing_group=True, exclude_noinput=False):
        raw_type = (
            ArcaeaNoteEventType.ARC_SKY if arc.is_skyline else ArcaeaNoteEventType.ARC_FLOOR
        )
        kind = map_arcaea_type_to_kind(raw_type)

        sample = Sample(arc)  # uses arc.t1/t2, x1/x2, y1/y2, easing [2](https://onedrive.live.com/personal/d5d62a1ef303ba22/_layouts/15/doc.aspx?resid=ee88c222-ce00-4968-8aad-d04f7ce2fa68&cid=d5d62a1ef303ba22)

        # Sample along the arc at the same rate as renderer (arc_sampling_rate is in theme_local).
        # Here we rely on Sample.get_coordinate_list which yields (x_pixel, t_ms, alpha). [2](https://onedrive.live.com/personal/d5d62a1ef303ba22/_layouts/15/doc.aspx?resid=ee88c222-ce00-4968-8aad-d04f7ce2fa68&cid=d5d62a1ef303ba22)
        for x_pixel, t_ms, alpha in sample.get_coordinate_list(sampling_rate=10):
            time_beats = _ms_to_beats(chart, t_ms)
            x_norm, z_norm = sample.get_coordinate_tuple(t_ms)  # normalized x,z in [-0.5..1.5], [0..1] [2](https://onedrive.live.com/personal/d5d62a1ef303ba22/_layouts/15/doc.aspx?resid=ee88c222-ce00-4968-8aad-d04f7ce2fa68&cid=d5d62a1ef303ba22)

            note_events.append({
                "time_beats": time_beats,
                "lane": 0,  # arcs are continuous; lane less meaningful, geometry in extra
                "kind": kind,  # hold_path
                "extra": {
                    "raw_type": raw_type.value,
                    "time_ms": t_ms,
                    "width_lanes": 1,
                    "shape": "arc",
                    "arc_x_norm": x_norm,
                    "arc_z_norm": z_norm,
                    "alpha": alpha,
                },
            })

    # --- ArcTaps (on skyline arcs) ---
    for arc in chart.get_command_list_for_type(Arc, search_in_timing_group=True, exclude_noinput=False):
        if not arc.arctap_list:
            continue

        sample = Sample(arc)
        for arctap in arc.arctap_list:
            raw_type = ArcaeaNoteEventType.ARCTAP
            kind = map_arcaea_type_to_kind(raw_type)

            t_ms = arctap.tn
            time_beats = _ms_to_beats(chart, t_ms)
            x_norm, z_norm = sample.get_coordinate_tuple(t_ms)  # normalized arc coordinate [2](https://onedrive.live.com/personal/d5d62a1ef303ba22/_layouts/15/doc.aspx?resid=ee88c222-ce00-4968-8aad-d04f7ce2fa68&cid=d5d62a1ef303ba22)

            note_events.append({
                "time_beats": time_beats,
                "lane": 0,
                "kind": kind,  # flick_arrow
                "extra": {
                    "raw_type": raw_type.value,
                    "time_ms": arctap.tn,
                    "width_lanes": 1,
                    "shape": "arc",
                    "arc_x_norm": x_norm,
                    "arc_z_norm": z_norm,
                    "direction": "up",  # placeholder; can be refined if you infer direction
                },
            })

    # --- Flicks (free flick notes) ---
    for flick in chart.get_command_list_for_type(Flick, search_in_timing_group=True, exclude_noinput=False):
        raw_type = ArcaeaNoteEventType.FLICK
        kind = map_arcaea_type_to_kind(raw_type)

        time_beats = _ms_to_beats(chart, flick.t)

        note_events.append({
            "time_beats": time_beats,
            "lane": 0,  # free flicks are not bound to ground lanes
            "kind": kind,  # flick_arrow
            "extra": {
                "raw_type": raw_type.value,
                "time_ms": flick.t,
                "width_lanes": 1,
                "shape": "free_flick",
                "x": flick.x,
                "y": flick.y,
                "vx": flick.vx,
                "vy": flick.vy,
            },
        })

    return chart_meta, note_events

from .arcaea_element import Chart, Tap, Hold, Arc, ArcTap, Flick  # [1](https://onedrive.live.com?cid=D5D62A1EF303BA22&id=D5D62A1EF303BA22!s940d924464344bc497557e8e5dfecbbc)
from .arcaea_note_event_type import ArcaeaNoteEventType  # 


from typing import Any, Dict, List
from .arcaea_element import Chart, Tap, Hold, Arc, ArcTap, Flick  # [1](https://onedrive.live.com?cid=D5D62A1EF303BA22&id=D5D62A1EF303BA22!s940d924464344bc497557e8e5dfecbbc)
from .arcaea_note_event_type import ArcaeaNoteEventType  # 


def validate_note_events(chart: Chart, note_events: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Validate canonical note_events against the original Arcaea Chart.

    Checks:
      - Tap / ArcTap / Flick counts vs Chart.get_combo_of(...)
      - #Hold objects vs #HOLD_START events
      - #Arc objects vs presence of ARC_* events
      - Derived combo decomposition:
          total_combo == single_combo + hold_long_combo + arc_long_combo

    Note:
      - Long-note combo contributions (Hold / Arc) are derived using
        Chart.get_long_note_combo(...) as defined in `arcaea_element.py`,
        not computed from note_events ticks. [1](https://onedrive.live.com?cid=D5D62A1EF303BA22&id=D5D62A1EF303BA22!s940d924464344bc497557e8e5dfecbbc)
    """

    report: Dict[str, Any] = {
        "expected": {},
        "actual": {},
        "derived": {},
        "ok": True,
        "errors": [],
    }

    from typing import List, Dict, Any
from .arcaea_element import Chart  # [1](https://onedrive.live.com?cid=D5D62A1EF303BA22&id=D5D62A1EF303BA22!s940d924464344bc497557e8e5dfecbbc)
from .arcaea_note_event_type import ArcaeaNoteEventType  # 


def validate_note_events_by_sections(
    chart: Chart,
    note_events: List[Dict[str, Any]],
    section_boundaries_ms: List[int],
) -> Dict[str, Any]:
    """
    Per-section combo validation for Arcaea charts.

    Parameters
    ----------
    chart : Chart
        Parsed Arcaea chart (AFF) as defined in `arcaea_element.py`. [1](https://onedrive.live.com?cid=D5D62A1EF303BA22&id=D5D62A1EF303BA22!s940d924464344bc497557e8e5dfecbbc)
    note_events : list[NoteEvent]
        Canonical note events emitted by `normalize_events`. Each event's extra
        dict is expected to include `extra["time_ms"] = original_time_ms`.
    section_boundaries_ms : list[int]
        Sorted ascending list of section end times in ms.
        Section 0 is [0, section_boundaries_ms[0]),
        section i is [section_boundaries_ms[i-1], section_boundaries_ms[i]),
        and the last section implicitly ends at chart.end_time if needed.

    Returns
    -------
    report : dict
        {
          "sections": [
            {
              "index": int,
              "start_ms": int,
              "end_ms": int,
              "expected_total_combo": int,
              "actual_single_events": int,
              "actual_long_structural": {
                  "hold_start_events": int,
                  "arc_events": int
              }
            }, ...
          ],
          "expected_total_combo": int,
          "sum_expected_section_combo": int,
          "ok": bool,
          "errors": [str, ...]
        }
    """
    report: Dict[str, Any] = {
        "sections": [],
        "expected_total_combo": chart.get_total_combo(),  # true game combo [1](https://onedrive.live.com?cid=D5D62A1EF303BA22&id=D5D62A1EF303BA22!s940d924464344bc497557e8e5dfecbbc)
        "sum_expected_section_combo": 0,
        "ok": True,
        "errors": [],
    }

    # Ensure boundaries are sorted and clipped to chart duration
    start_ms = 0
    end_chart_ms = chart.get_interval()[1]  # (start, end) in ms [1](https://onedrive.live.com?cid=D5D62A1EF303BA22&id=D5D62A1EF303BA22!s940d924464344bc497557e8e5dfecbbc)
    boundaries = [b for b in sorted(section_boundaries_ms) if 0 < b < end_chart_ms]
    boundaries.append(end_chart_ms)  # ensure last section ends at chart end

    from .arcaea_element import Tap, ArcTap, Flick, Hold, Arc  # for type hints / iteration [1](https://onedrive.live.com?cid=D5D62A1EF303BA22&id=D5D62A1EF303BA22!s940d924464344bc497557e8e5dfecbbc)

    section_index = 0
    prev_combo_prefix = chart.get_total_combo_before(start_ms)  # should be 0 at t=0 [1](https://onedrive.live.com?cid=D5D62A1EF303BA22&id=D5D62A1EF303BA22!s940d924464344bc497557e8e5dfecbbc)

    for end_ms in boundaries:
        combo_prefix_end = chart.get_total_combo_before(end_ms)  # combo up to end_ms [1](https://onedrive.live.com?cid=D5D62A1EF303BA22&id=D5D62A1EF303BA22!s940d924464344bc497557e8e5dfecbbc)
        expected_section_combo = combo_prefix_end - prev_combo_prefix

        report["sum_expected_section_combo"] += expected_section_combo

        # Actual NoteEvents in this section: [start_ms, end_ms)
        section_events = [
            ev for ev in note_events
            if start_ms <= ev.get("extra", {}).get("time_ms", 0) < end_ms
        ]

        # Single-hit events in this section (Tap / ArcTap / Flick)
        single_raw_types = {
            ArcaeaNoteEventType.TAP.value,
            ArcaeaNoteEventType.ARCTAP.value,
            ArcaeaNoteEventType.FLICK.value,
        }
        actual_single_events = sum(
            1
            for ev in section_events
            if ev.get("extra", {}).get("raw_type") in single_raw_types
        )

        # Structural long-note info
        actual_hold_start_events = sum(
            1
            for ev in section_events
            if ev.get("extra", {}).get("raw_type") == ArcaeaNoteEventType.HOLD_START.value
        )
        actual_arc_events = sum(
            1
            for ev in section_events
            if ev.get("extra", {}).get("raw_type") in {
                ArcaeaNoteEventType.ARC_FLOOR.value,
                ArcaeaNoteEventType.ARC_SKY.value,
            }
        )

        section_info = {
            "index": section_index,
            "start_ms": start_ms,
            "end_ms": end_ms,
            "expected_total_combo": expected_section_combo,
            "actual_single_events": actual_single_events,
            "actual_long_structural": {
                "hold_start_events": actual_hold_start_events,
                "arc_events": actual_arc_events,
            },
        }
        report["sections"].append(section_info)

        # Move to next section
        start_ms = end_ms
        prev_combo_prefix = combo_prefix_end
        section_index += 1

    # Sanity check: sum of per-section expected combos == chart total combo
    if report["sum_expected_section_combo"] != report["expected_total_combo"]:
        report["ok"] = False
        report["errors"].append(
            "Sum of per-section combo does not match Chart.get_total_combo(): "
            f"{report['sum_expected_section_combo']} vs {report['expected_total_combo']}."
        )

    return report


    # --- Expected counts from Chart (native) ---

    # Single-hit combo
    expected_tap = chart.get_combo_of(Tap)        # taps [1](https://onedrive.live.com?cid=D5D62A1EF303BA22&id=D5D62A1EF303BA22!s940d924464344bc497557e8e5dfecbbc)
    expected_arctap = chart.get_combo_of(ArcTap)  # arc taps [1](https://onedrive.live.com?cid=D5D62A1EF303BA22&id=D5D62A1EF303BA22!s940d924464344bc497557e8e5dfecbbc)
    expected_flick = chart.get_combo_of(Flick)    # flicks [1](https://onedrive.live.com?cid=D5D62A1EF303BA22&id=D5D62A1EF303BA22!s940d924464344bc497557e8e5dfecbbc)
    expected_single_combo = expected_tap + expected_arctap + expected_flick

    # Long-note combo (Hold + Arc) using get_long_note_combo
    # Holds: we can pass the iterator directly
    expected_hold_long_combo = chart.get_long_note_combo(
        chart.get_command_list_for_type(Hold)
    )  # [1](https://onedrive.live.com?cid=D5D62A1EF303BA22&id=D5D62A1EF303BA22!s940d924464344bc497557e8e5dfecbbc)

    # Arcs: use the connected arc list (handles has_head, continuity)
    expected_arc_long_combo = chart.get_long_note_combo(chart._connected_arc_list)  # [1](https://onedrive.live.com?cid=D5D62A1EF303BA22&id=D5D62A1EF303BA22!s940d924464344bc497557e8e5dfecbbc)

    expected_long_combo_total = expected_hold_long_combo + expected_arc_long_combo

    # Total combo as reported by Chart
    expected_total_combo = chart.get_total_combo()  # [1](https://onedrive.live.com?cid=D5D62A1EF303BA22&id=D5D62A1EF303BA22!s940d924464344bc497557e8e5dfecbbc)

    # Derived from parts (sanity check on Chart's own combo decomposition)
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

    # Check that Chart's decomposition is internally consistent
    if derived_total_combo_from_parts != expected_total_combo:
        report["ok"] = False
        report["errors"].append(
            f"Total combo mismatch inside Chart: "
            f"get_total_combo()={expected_total_combo}, "
            f"but single_combo + long_combo_total={derived_total_combo_from_parts}."
        )

    # --- Actual counts from canonical note_events ---

    actual_tap = 0
    actual_arctap = 0
    actual_flick = 0

    hold_start_events = 0
    arc_events = 0

    for ev in note_events:
        extra = ev.get("extra", {})
        raw_type = extra.get("raw_type")

        if raw_type == ArcaeaNoteEventType.TAP.value:
            actual_tap += 1
        elif raw_type == ArcaeaNoteEventType.ARCTAP.value:
            actual_arctap += 1
        elif raw_type == ArcaeaNoteEventType.FLICK.value:
            actual_flick += 1
        elif raw_type == ArcaeaNoteEventType.HOLD_START.value:
            hold_start_events += 1
        elif raw_type in (ArcaeaNoteEventType.ARC_FLOOR.value, ArcaeaNoteEventType.ARC_SKY.value):
            arc_events += 1

    report["actual"] = {
        "tap_events": actual_tap,
        "arctap_events": actual_arctap,
        "flick_events": actual_flick,
        "hold_start_events": hold_start_events,
        "arc_events": arc_events,
    }

    # --- Checks ---

    # 1) Single-hit notes: Tap, ArcTap, Flick should match exactly
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

    # 2) Long notes (structural checks, not exact tick counts)
    if hold_start_events != expected_hold_objects:
        report["ok"] = False
        report["errors"].append(
            f"Hold start mismatch: expected {expected_hold_objects} Hold objects, "
            f"got {hold_start_events} HOLD_START note_events"
        )

    if arc_events < expected_arc_objects:
        report["ok"] = False
        report["errors"].append(
            f"Arc events mismatch: expected at least {expected_arc_objects} Arc objects, "
            f"but only found {arc_events} ARC_* note_events (sampled)."
        )

    return report


from typing import List, Dict, Any
from .arcaea_element import Chart, Tap, ArcTap, Flick, Hold, Arc  # [1](https://onedrive.live.com?cid=D5D62A1EF303BA22&id=D5D62A1EF303BA22!s940d924464344bc497557e8e5dfecbbc)


def build_sections_from_boundaries(
    chart: Chart,
    note_events: List[Dict[str, Any]],
    section_boundaries_ms: List[int],
) -> List[Dict[str, Any]]:
    """
    Build SectionMetrics aligned EXACTLY with validate_note_events_by_sections.

    Each section is:
       [start_ms, end_ms)
    using the same Chart timing semantics and the same NoteEvent time_ms.

    Returns a list of:
    {
       "start_ms": int,
       "end_ms": int,
       "start_beats": float,
       "end_beats": float,
       "expected_total_combo": int,    # true combo in this window
       "actual_single_events": int,    # TAP / ARCTAP / FLICK
       "actual_long_structural": {
           "hold_start_events": int,
           "arc_events": int
       },
       "npb": s.npb,
       "nps": s.nps,
       "meta": {}                      # extensible
    }
    """
    # Ensure sorted boundaries
    start_ms = 0
    end_chart_ms = chart.get_interval()[1]  # [1](https://onedrive.live.com?cid=D5D62A1EF303BA22&id=D5D62A1EF303BA22!s940d924464344bc497557e8e5dfecbbc)
    boundaries = [b for b in sorted(section_boundaries_ms) if 0 < b < end_chart_ms]
    boundaries.append(end_chart_ms)

    from .adapter_arcaea import _ms_to_beats  # same helper you used in normalize_events

    sections: List[Dict[str, Any]] = []
    prev_combo_prefix = chart.get_total_combo_before(start_ms)  # [1](https://onedrive.live.com?cid=D5D62A1EF303BA22&id=D5D62A1EF303BA22!s940d924464344bc497557e8e5dfecbbc)

    for end_ms in boundaries:
        combo_prefix_end = chart.get_total_combo_before(end_ms)
        expected_combo = combo_prefix_end - prev_combo_prefix

        # slice noteEvents in this window
        section_events = [
            ev for ev in note_events
            if start_ms <= ev.get("extra", {}).get("time_ms", -1) < end_ms
        ]

        # Compute singles
        single_raw_types = {
            ArcaeaNoteEventType.TAP.value,
            ArcaeaNoteEventType.ARCTAP.value,
            ArcaeaNoteEventType.FLICK.value,
        }
        actual_single_events = sum(
            1 for ev in section_events
            if ev.get("extra", {}).get("raw_type") in single_raw_types
        )

        # Structural long-note events
        hold_start_events = sum(
            1 for ev in section_events
            if ev.get("extra", {}).get("raw_type") == ArcaeaNoteEventType.HOLD_START.value
        )
        arc_events = sum(
            1 for ev in section_events
            if ev.get("extra", {}).get("raw_type") in {
                ArcaeaNoteEventType.ARC_FLOOR.value,
                ArcaeaNoteEventType.ARC_SKY.value,
            }
        )

        # Convert window to beats
        start_beats = _ms_to_beats(chart, start_ms)
        end_beats = _ms_to_beats(chart, end_ms)

        # density calculations
        duration_s = max(0.001, (end_ms - start_ms) / 1000)
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
            "meta": {},
        })

        # advance window
        start_ms = end_ms
        prev_combo_prefix = combo_prefix_end

    return sections

def _infer_song_id_from_path(path: str) -> str:
    """
    Infer Arcaea song_id from an AFF path.

    Assumes filenames are of the form:
      <song_id>.aff
    or
      <song_id>_<something>.aff

    You can refine this if your naming conventions differ.
    """
    base = os.path.basename(path)
    name, _ = os.path.splitext(base)
    return name.split("_")[0]


def _map_arcaea_diff_code(num: int) -> str:
    """
    Map arcsong.json's numeric difficulty code to tier.

    Derived from patterns in arcsong.json:
      - codes >= 20 are highest tier (BYD)
      - codes 16–19 are high FTR
      - codes 12–15 are PRS
      - codes < 12 are PST
    """
    if num >= 20:
        return "BYD"
    elif num >= 16:
        return "FTR"
    elif num >= 12:
        return "PRS"
    else:
        return "PST"


def _lookup_chart_difficulty_details(song_id: str, chart: Chart) -> Dict[str, Any] | None:
    """
    Look up original difficulty info for (song_id, chart) from arcsong.json.

    Uses Chart.get_total_combo() as the note total and finds the closest
    matching difficulty entry by 'note' in arcsong.json. [2](https://onedrive.live.com?cid=D5D62A1EF303BA22&id=D5D62A1EF303BA22!sddba83390cce4b54973b863db55e8c49)[1](https://onedrive.live.com?cid=D5D62A1EF303BA22&id=D5D62A1EF303BA22!s0d6babc44a7a4ed698aad027e9f6d0f6)

    Returns a dict like:
      {
        "song_id": str,
        "name_en": str,
        "difficulty_code": int,
        "rating_raw": int,
        "level": int,
        "note": int,
        "tier": str,        # PST/PRS/FTR/BYD
        "label": str,       # "<TIER> <LEVEL>",
        "note_delta": int,  # |chart_total_combo - note|
        "is_consistent": bool
      }
    or None if not found.
    """
    total_combo = chart.get_total_combo()  # true combo from parsed chart [2](https://onedrive.live.com?cid=D5D62A1EF303BA22&id=D5D62A1EF303BA22!sddba83390cce4b54973b863db55e8c49)

    for s in _ARCSONG_DB:
        if s["song_id"] == song_id:
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

            diff_code = best.get("difficulty")   # numeric difficulty code [1](https://onedrive.live.com?cid=D5D62A1EF303BA22&id=D5D62A1EF303BA22!s0d6babc44a7a4ed698aad027e9f6d0f6)
            rating_raw = best.get("rating")      # arcsong.json 'rating'
            note = best.get("note")              # arcsong.json 'note' (total notes/combo)
            name_en = best.get("name_en")

            if rating_raw is None or diff_code is None or note is None:
                return None

            level = rating_raw // 5
            tier = _map_arcaea_diff_code(diff_code)
            label = f"{tier} {level}"

            # Consistency: small mismatch allowed; large mismatch is suspicious.
            note_delta = abs(total_combo - note)
            # You can tune this threshold; 10 is a reasonable default.
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


def to_canonical_payload(source_ref: str) -> CanonicalChartPayload:
    """
    Main entrypoint: convert an Arcaea chart into canonical payload.
    """
    # 1) Load AFF and parse into Chart
    chart = load_chart(source_ref)

    # 2) Normalize into canonical note_events and chart_meta
    chart_meta, note_events = normalize_events(chart)

    # 3) Infer song_id from path and look up difficulty in arcsong.json
    song_id = _infer_song_id_from_path(source_ref)
    diff_info = _lookup_chart_difficulty_details(song_id, chart)
    if diff_info is not None:
        difficulty_label = diff_info["label"]  # e.g. "FTR 11", "BYD 12"
    else:
        difficulty_label = ""

    # 4) Build SectionMetrics (uniform 8 sections by default)
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
        density_nps,
        density_npb, 
    )

    # --- Phase 3 wiring: normalize section keys to pipeline.section_metrics contract ---
    # pipeline.section_metrics.aggregate_sections expects "nps" and "npb". [1](https://onedrive.live.com?cid=D5D62A1EF303BA22&id=D5D62A1EF303BA22!s91dad12b2839483c82a307518255d9cc)
    # This adapter currently produces "density_nps"/"density_npb". [3](https://onedrive.live.com?cid=D5D62A1EF303BA22&id=D5D62A1EF303BA22!s940d924464344bc497557e8e5dfecbbc)
    if isinstance(sections, list) and sections:
        normalized_sections: List[Dict[str, Any]] = []
        for s in sections:
            if not isinstance(s, dict):
                continue
            s2 = dict(s)

            # Alias density keys into canonical keys expected by aggregation.
            if "nps" not in s2 and isinstance(s2.get("density_nps"), (int, float)):
                s2["nps"] = float(s2["density_nps"])
            if "npb" not in s2 and isinstance(s2.get("density_npb"), (int, float)):
                s2["npb"] = float(s2["density_npb"])

            normalized_sections.append(s2)

        sections = normalized_sections

    # 5) Assemble adapter_metadata
    adapter_metadata: Dict[str, Any] = {
        "adapter_id": "adapter_arcaea_v1",
        "adapter_version": "1.0.0",
        "source_format": "aff",
        "source_path": source_ref,
        "notes": "Arcaea reference adapter using AFF + canonical NoteEvents.",
        "song_id": song_id,
    }

    # Attach original difficulty details + consistency info if available
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
            # You can record the threshold here too if you want to change it later
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

    # 6) Aggregate diagnostics from sections (for QA dashboards)
    diagnostics: Dict[str, Any] = {}
    if sections:
        # sections come from build_sections_from_boundaries and include density_nps / density_npb 
        try:
            avg_nps = sum(s.get("density_nps", 0.0) for s in sections) / len(sections)
        except ZeroDivisionError:
            avg_nps = 0.0

        try:
            avg_npb = sum(s.get("density_npb", 0.0) for s in sections) / len(sections)
        except ZeroDivisionError:
            avg_npb = 0.0

        diagnostics.update(
            {
                "sections_count": len(sections),
                "avg_nps": avg_nps,
                "avg_npb": avg_npb,
            }
        )

    # 7) Internal tracking metadata (ingestion / QA only)
    internal_metadata: Dict[str, Any] = {
        "sections_source": "adapter_arcaea.build_sections_from_boundaries",
        "adapter_id": adapter_metadata.get("adapter_id"),
        "adapter_version": adapter_metadata.get("adapter_version"),
    }

    # 8) Assemble canonical payload (aligned with canonical_chart_payload_schema.json)
    from rhythm_ingestion.pipeline.section_metrics import SECTION_METRICS_VERSION
    payload: CanonicalChartPayload = {
        "game_id": "arcaea",
        "chart_id": source_ref,
        "difficulty": difficulty_label,
        "note_events": note_events,
        "chart_meta": chart_meta,
        "adapter_metadata": adapter_metadata,
        "diagnostics": diagnostics,
        "internal_metadata": internal_metadata,
        "sections": sections,
        "canonical_sections_version": SECTION_METRICS_VERSION,
    }

    return payload

from pathlib import Path
from .base_adapter import BaseAdapter

class ArcaeaAdapter(BaseAdapter):
    game_id = "arcaea"

    def accepts_file(self, path: Path) -> bool:
        return str(path).lower().endswith(".aff")

    def load(self, path: Path):
        # raw_chart can be the parsed Chart object
        return load_chart(str(path))

    def to_canonical_payload(self, source_ref: str) -> dict:
        # reuse your existing module-level builder
        return to_canonical_payload(source_ref)

    def to_canonical_row(self, raw) -> dict:
        # minimal row; you can extend using arcsong lookup later
        # raw is Chart from load()
        chart = raw
        start_ms, end_ms = chart.get_interval()
        duration_ms = int(end_ms - start_ms)
        return {
            "game": "arcaea",
            "song_id": None,
            "difficulty_label": None,
            "note_total_chart": int(chart.get_total_combo()),
            "duration_ms": duration_ms,
        }

    def capabilities(self) -> dict:
        return {
            "note_model": "spatial",
            "supports_sections": True,
            "supports_variable_bpm": True,
            "supports_ground_truth_chart": True,
            "emits_canonical_payload": True,
        }

__all__ = [
    "ArcaeaAdapter",
    "to_canonical_payload",
    "load_chart",
]
